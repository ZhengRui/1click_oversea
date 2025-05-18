class Slice:
    """
    A Slice represents a single unit of data extraction.
    It includes a config with extraction parameters and optional processors.
    """

    def __init__(self, config, pre_processor=None, post_processor=None):
        """
        Initialize a Slice for data extraction.

        Args:
            config (dict): Configuration dictionary with extraction parameters
                (name, selector, type, fields, etc.)
            pre_processor (callable, optional): Function to preprocess the element before extraction
                (overrides pre_processor in config if provided)
            post_processor (callable, optional): Function to postprocess the extracted data
                (overrides post_processor in config if provided)
        """
        self.config = config.copy()

        # Extract processors from config if not provided externally
        self.pre_processor = pre_processor or config.get('pre_processor')
        self.post_processor = post_processor or config.get('post_processor')

        # Remove processors from config copy to avoid duplication
        if 'pre_processor' in self.config:
            del self.config['pre_processor']
        if 'post_processor' in self.config:
            del self.config['post_processor']

        # Extract commonly used attributes from config for convenience
        self.name = self.config.get("name")
        self.selector = self.config.get("selector")
        self.type = self.config.get("type", "text")

    def to_dict(self):
        """Convert the slice to a dictionary representation for the extractor."""
        result = self.config.copy()
        return result

    def process_data(self, data):
        """Apply post_processor to extracted data if available."""
        if self.post_processor and data is not None:
            return self.post_processor(data)
        return data
