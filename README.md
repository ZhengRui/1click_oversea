# 1Click Oversea Conversion Framework

A modular framework for converting Chinese online webshop pages (such as Alibaba 1688) into structured formats suitable for deployment on international e-commerce platforms like Shopee, Shopify, and more.

This framework is designed to automate the process of:
- Extracting (scraping) product data from Chinese e-commerce sites
- Translating and transforming the data
- Preparing the data for seamless listing on global platforms

## Features

- Modular architecture with `Slice` and `Pipeline` classes for data extraction
- Automatic pipeline registration mechanism
- Headless browser automation using `crawl4ai`
- Flexible data processing with pre/post-processors
- JSON output with structured product data

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/1click_oversea.git
cd 1click_oversea
```

2. Create and activate a virtual environment:
```bash
# Install uv if you don't have it already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate
```

3. Install dependencies:
```bash
# Install dependencies from the lockfile
uv sync --frozen
```

## Usage

Before running the main script, you need to create a user data directory for crawl4ai to use for identity-based crawling:

1. Create a user data directory using one of the methods described in the [crawl4ai documentation](https://docs.crawl4ai.com/advanced/identity-based-crawling/):

```bash
# Find Playwright Chromium binary path first
python -m playwright install --dry-run

# Then launch Chromium with a custom user data directory
# Replace the path below with the actual path from the previous command
~/.cache/ms-playwright/chromium-1234/chrome-linux/chrome \
    --user-data-dir=/path/to/my_chrome_profile

# On macOS:
# ~/Library/Caches/ms-playwright/chromium-1234/chrome-mac/Chromium.app/Contents/MacOS/Chromium \
#     --user-data-dir=/Users/<you>/my_chrome_profile

# On Windows:
# "C:\Users\<you>\AppData\Local\ms-playwright\chromium-1234\chrome-win\chrome.exe" ^
#     --user-data-dir="C:\Users\<you>\my_chrome_profile"
```

2. Edit the `lib/pipelines/alibaba_1688.py` file to update the `user_data_dir` path to your newly created directory.

3. Run the main script to extract data from Alibaba 1688:

    ```bash
    usage: main.py [-h] [--pipeline PIPELINE] --url URL [--headless] [--dump_to DUMP_TO] [--translate]
                  [--translated_output TRANSLATED_OUTPUT]

    Run product extraction pipeline.

    options:
      -h, --help            show this help message and exit
      --pipeline PIPELINE   Pipeline name to use (default: alibaba_1688)
      --url URL             Product URL to scrape
      --headless            Run browser in headless mode
      --dump_to DUMP_TO     Output file location (if set, will also print)
      --wait_for WAIT_FOR   Delay before returning HTML in seconds (default: 10)
    ```

   a. The first time you run the script, use it in headful mode (without `--headless` flag) to sign in to 1688.com:
   ```bash
   python main.py --pipeline alibaba_1688 --url https://detail.1688.com/offer/865196865369.html --dump_to data/example_product_data.json
   ```

   b. When the browser opens, sign in to your 1688.com account. The credentials will be saved in your user data directory.

   c. For subsequent runs, you can use headless mode for faster processing:
   ```bash
   python main.py --pipeline alibaba_1688 --url https://detail.1688.com/offer/865196865369.html --dump_to data/example_product_data.json --headless
   ```

   d. To improve performance, you can adjust the crawling delay using the `--wait_for` parameter:
   ```bash
   # Use a shorter delay (2 seconds instead of the default 10 seconds)
   python main.py --pipeline alibaba_1688 --url https://detail.1688.com/offer/865196865369.html --headless --wait_for 2
   ```

   The `wait_for` parameter controls the `delay_before_return_html` setting in crawl4ai, which determines how long to wait before capturing the final HTML. According to the crawl4ai documentation, the default value is 0.1 seconds, but for complex sites like 1688.com, we use a higher default (10 seconds) to ensure all dynamic content loads properly.

   - **Lower values (1-2 seconds)**: Faster processing but may miss some dynamic content
   - **Higher values (5-10 seconds)**: More reliable content extraction but slower processing

   Example product URLs with different layouts:
   ```
   # https://detail.1688.com/offer/718654342849.html
   # https://detail.1688.com/offer/802350325795.html
   # https://detail.1688.com/offer/640756097760.html
   # https://detail.1688.com/offer/764286652699.html
   ```

4. Serve the API endpoint for integration with other applications:

   a. Start the FastAPI server:
   ```bash
   python serv.py
   ```

   b. The API will be available at http://localhost:8000 with the following endpoints:
      - `/` - Basic information about the API
      - `/extract` - Extract product data from a URL

   c. Example API usage with curl:
   ```bash
   # Extract data from a URL with default settings (pipeline=alibaba_1688, wait_for=2)
   curl -X GET "http://localhost:8000/extract?url=https://detail.1688.com/offer/865196865369.html"

   # Extract data with a custom wait time (1 second)
   curl -X GET "http://localhost:8000/extract?url=https://detail.1688.com/offer/865196865369.html&wait_for=1"

   # Extract data with a different pipeline
   curl -X GET "http://localhost:8000/extract?url=https://detail.1688.com/offer/865196865369.html&pipeline_name=custom_pipeline"
   ```

   d. The API runs in headless mode by default with a shorter wait time (2 seconds) for better performance. This is suitable for production environments where browser UI is not needed.

## Project Structure

- `lib/`: Core framework components
  - `pipeline.py`: Pipeline class for orchestrating data extraction
  - `slice.py`: Slice class for defining extraction units
  - `registry.py`: Registry for pipeline management
  - `pipelines/`: Individual pipeline implementations
    - `alibaba_1688.py`: 1688.com-specific pipeline
- `utils/`: Utility scripts
  - `highlight.js`: JavaScript for highlighting elements
  - `simHover.js`: JavaScript for simulating hover events
- `data/`: Output directory for extracted data
- `main.py`: Main script to run the extraction

## Creating Custom Pipelines

1. Create a new file in the `lib/pipelines/` directory
2. Define slice configurations and post-processing functions
3. Create and register a pipeline factory function:

```python
@PipelineRegistry.register_pipeline(name="your_pipeline_name")
def create_your_pipeline():
    pipeline = Pipeline(name="YourPipeline", configs=YOUR_CONFIG)
    return pipeline
```

4. Import the pipeline module in `lib/pipelines/__init__.py`


## Limitations

- **Video URLs:** The `product_images` slice marks videos with `is_video`, but does not extract video URLs.
- **Dynamic SKU Data:** Price and stock in SKU sections may change with user interaction; only initial values are extracted.
- **User Interactions:** Data requiring clicks, hovers, or scrolling may not be fully extracted, as full interaction simulation is not implemented.

## License

MIT
