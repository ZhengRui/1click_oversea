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

url = "https://detail.1688.com/offer/764286652699.html"


async def main():
    pipeline = PipelineRegistry.get("alibaba_1688")

    if not pipeline:
        ic("Error: Alibaba 1688 pipeline not found in registry")
        return

    try:
        ic("Running pipeline with URL:", url)

        processed_data = await pipeline.run(url=url)

        formatted_data = json.dumps(processed_data, indent=2, ensure_ascii=False)
        ic("Processing complete. Extracted data:")
        print(formatted_data)

        base_dir = Path(__file__).parent
        output_dir = base_dir / "data"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "example_product_data.json"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(formatted_data)

        ic("Data saved to:", output_file)

    except Exception as e:
        ic("Error during pipeline execution:", e)

    ic("Run completed.")


if __name__ == "__main__":
    asyncio.run(main())
