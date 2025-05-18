from typing import Any, Callable, Dict, List, Optional, Set, Union

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from .slice import Slice


class Pipeline:
    """
    A Pipeline is a collection of slices that collectively extract
    structured data from a webpage.
    """

    def __init__(
        self,
        name: str,
        base_selector: str = "body",
        configs: Union[List[Dict], Dict] = None,
        post_processor: Callable[[Dict[str, Any]], Dict[str, Any]] = None,
    ):
        """
        Initialize a Pipeline for data extraction.

        Args:
            name (str): Name of the pipeline
            base_selector (str): Base CSS selector to start extraction from
            configs (Union[List[Dict], Dict], optional): Either a list of slice configurations
                or a dictionary with 'browser', 'run', and 'slices' configurations
            post_processor (Callable, optional): Function to process the final data after
                extraction and slice processing
        """
        self.name = name
        self.base_selector = base_selector
        self.slices: List[Slice] = []
        self._selectors: List[str] = []
        self.post_processor = post_processor

        # Configuration settings
        self.browser_config = None
        self.run_config = None

        # Initialize from configs if provided
        if configs:
            self._init_from_configs(configs)

    def _init_from_configs(self, configs: Union[List[Dict], Dict]) -> None:
        """
        Initialize pipeline from configuration.

        Args:
            configs: Either a list of slice configurations or a dictionary with
                    'browser', 'run', and 'slices' configurations
        """
        # Handle dictionary config format with browser, run, slices
        if isinstance(configs, dict):
            # Set browser config if provided
            if 'browser' in configs:
                browser_params = configs.get('browser', {})
                self.browser_config = BrowserConfig(**browser_params)

            # Set run config if provided
            if 'run' in configs:
                run_params = configs.get('run', {})

                # Save the extraction_strategy for later
                if 'extraction_strategy' in run_params:
                    del run_params['extraction_strategy']

                self.run_config = CrawlerRunConfig(**run_params)

            # Initialize slices from slice configs
            slice_configs = configs.get('slices', [])
            for config in slice_configs:
                self.add_slice(Slice(config))

        # Handle list of slice configs (legacy format)
        elif isinstance(configs, list):
            for config in configs:
                self.add_slice(Slice(config))

    def add_slice(self, slice_obj: Slice) -> None:
        """Add a slice to the pipeline."""
        self.slices.append(slice_obj)
        # Clear selector cache when adding a slice
        self._selectors = []

    def add_slices(self, slices: List[Slice]) -> None:
        """Add multiple slices to the pipeline."""
        self.slices.extend(slices)
        # Clear selector cache when adding slices
        self._selectors = []

    def add_from_configs(self, configs: List[Dict]) -> None:
        """Add slices from configuration dictionaries."""
        for config in configs:
            self.add_slice(Slice(config))

    def to_extraction_strategy(self) -> JsonCssExtractionStrategy:
        """Convert the pipeline to a JsonCssExtractionStrategy for crawl4ai."""
        fields = [slice_obj.to_dict() for slice_obj in self.slices]

        schema = {"name": self.name, "baseSelector": self.base_selector, "fields": fields}

        return JsonCssExtractionStrategy(schema)

    def _extract_selectors(self, field_list: List[Dict], parent_selector: str = "") -> List[str]:
        """
        Extract all CSS selectors from the schema.

        Args:
            field_list: List of field dictionaries
            parent_selector: Parent selector for nested fields

        Returns:
            List of all CSS selectors
        """
        selectors = []

        for field in field_list:
            if "selector" in field:
                if parent_selector:
                    selector = f"{parent_selector} {field['selector']}"
                else:
                    selector = field['selector']
                selectors.append(selector)

            if "fields" in field:
                new_parent = ""
                if "selector" in field:
                    new_parent = field["selector"] if not parent_selector else f"{parent_selector} {field['selector']}"
                elif parent_selector:
                    new_parent = parent_selector

                selectors.extend(self._extract_selectors(field["fields"], new_parent))

        return selectors

    @property
    def selectors(self) -> List[str]:
        """
        Get all CSS selectors used by this pipeline.

        Returns:
            List of all CSS selectors
        """
        if not self._selectors:
            # Extract selectors from the schema
            extraction_strategy = self.to_extraction_strategy()
            self._selectors = self._extract_selectors(extraction_strategy.schema["fields"])

        return self._selectors

    def get_crawler_configs(self) -> tuple:
        """
        Get the browser and run configurations for the crawler.

        Returns:
            Tuple of (BrowserConfig, CrawlerRunConfig)
        """
        # Use existing configs if set
        browser_config = self.browser_config

        # Create run config with current extraction strategy
        run_config = self.run_config
        if run_config:
            # Make a copy to avoid modifying the original
            run_config_dict = vars(run_config).copy()
            run_config_dict['extraction_strategy'] = self.to_extraction_strategy()
            run_config = CrawlerRunConfig(**run_config_dict)
        else:
            run_config = CrawlerRunConfig(extraction_strategy=self.to_extraction_strategy())

        return browser_config, run_config

    def process_data(self, data: Dict[str, Any], keep_keys: bool = False) -> Dict[str, Any]:
        """
        Process the extracted data through all slices' post_processors.

        Args:
            data (Dict[str, Any]): The data to process
            keep_keys (bool, optional): If True, keeps keys from data
                that aren't defined in slices. Default is False.

        Returns:
            Dict[str, Any]: The processed data
        """
        result = {}

        # Get all slice names for reference
        slice_names = [slice_obj.name for slice_obj in self.slices]

        # Process data through all slices
        for slice_obj in self.slices:
            slice_name = slice_obj.name
            if slice_name in data:
                result[slice_name] = slice_obj.process_data(data[slice_name])
            else:
                result[slice_name] = None

        # Keep additional keys if requested
        if keep_keys:
            for key, value in data.items():
                if key not in slice_names and key not in result:
                    result[key] = value

        return result

    async def run(self, url: str) -> Dict[str, Any]:
        """
        Run the pipeline on a URL.

        This method handles the entire process of:
        1. Setting up the crawler
        2. Running the crawler
        3. Processing the extracted data
        4. Applying the pipeline's post_processor if available
        5. Returning the processed result

        Args:
            url (str): The URL to scrape

        Returns:
            Dict[str, Any]: The processed data

        Raises:
            ValueError: If browser_config is not set
            RuntimeError: If the crawler run fails
        """
        # Check for browser config
        if not self.browser_config:
            raise ValueError("Pipeline browser_config must be set before running")

        # Get the crawler configs
        browser_config, run_config = self.get_crawler_configs()

        # Run the crawler
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)

            if not result.success:
                raise RuntimeError(f"Crawler run failed: {result.error_message}")

            if not result.extracted_content:
                return {}

            # Parse the extracted content
            import json

            try:
                extracted_data = json.loads(result.extracted_content)
            except json.JSONDecodeError:
                raise RuntimeError("Failed to parse extracted content as JSON")

            # Process the data
            processed_data = None

            if isinstance(extracted_data, list):
                for page_data in extracted_data:
                    # Add the URL to the raw data
                    page_data["url"] = url

                    # Process the data - always keep keys like 'url'
                    processed_data = self.process_data(page_data, keep_keys=True)
            else:
                # Handle case where extracted_data is not a list
                extracted_data["url"] = url
                processed_data = self.process_data(extracted_data, keep_keys=True)

            # Apply pipeline post-processor if it exists
            if self.post_processor and processed_data:
                processed_data = self.post_processor(processed_data)

            return processed_data
