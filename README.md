# 1Click Oversea Web Scraping Framework

A modular and flexible web scraping framework for extracting product data from e-commerce platforms, with a current focus on Alibaba's 1688.com wholesale platform.

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
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies using `uv`:
```bash
# Install uv if you don't have it already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies from the lockfile
uv sync --frozen
```

## Usage

Run the main script to extract data from Alibaba 1688:

```bash
python main.py
```

The script is configured with hard-coded settings in the `main.py` file. Edit the configuration parameters:

```python
config = {
    "url": "https://detail.1688.com/offer/764286652699.html",  # Product URL to scrape
    "headless": False,  # Set to True to run browser in background
    "output": "data/example_product_data.json",  # Output file location
    "print": True,  # Print results to console
}
```

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

## License

MIT
