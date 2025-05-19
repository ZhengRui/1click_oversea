"""
Main script for using the Alibaba 1688 pipeline implementation.

This script fetches product data from Alibaba's 1688.com wholesale platform
using the registered alibaba_1688 pipeline.
"""

import asyncio
import json
from pathlib import Path

from icecream import ic

from lib import PipelineRegistry


async def main():
    # Hard-coded configuration
    config = {
        "url": "https://detail.1688.com/offer/764286652699.html",
        # "url": "https://detail.1688.com/offer/865196865369.html",
        # "url": "https://detail.1688.com/offer/640756097760.html",
        # "url": "https://detail.1688.com/offer/802350325795.html",
        "headless": False,
        "output": "data/example_product_data.json",
        "print": True,
    }

    # Get the pipeline by its registered name
    pipeline = PipelineRegistry.get("alibaba_1688")

    if not pipeline:
        ic("Error: Alibaba 1688 pipeline not found in registry")
        return

    try:
        ic("Running pipeline with URL:", config["url"])
        ic("Headless mode:", config["headless"])
        ic("Output will be saved to:", config["output"])

        # Run the pipeline with the provided parameters
        processed_data = await pipeline.run(url=config["url"], headless=config["headless"], dump_to=config["output"])

        # Print the data if requested
        if config["print"]:
            formatted_data = json.dumps(processed_data, indent=2, ensure_ascii=False)
            ic("Processing complete. Extracted data:")
            print(formatted_data)
        else:
            ic("Processing complete. Data saved to:", config["output"])

    except Exception as e:
        ic("Error during pipeline execution:", e)

    ic("Run completed.")


if __name__ == "__main__":
    asyncio.run(main())
