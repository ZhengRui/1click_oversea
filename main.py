"""
Main script for using the Alibaba 1688 pipeline implementation.

This script fetches product data from Alibaba's 1688.com wholesale platform
using the registered alibaba_1688 pipeline.
"""

import argparse
import asyncio
import json
from pathlib import Path

from icecream import ic

from lib import PipelineRegistry


async def main():
    parser = argparse.ArgumentParser(description="Run product extraction pipeline.")
    parser.add_argument(
        '--pipeline', type=str, default='alibaba_1688', help='Pipeline name to use (default: alibaba_1688)'
    )
    parser.add_argument('--url', type=str, required=True, help='Product URL to scrape')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--dump_to', type=str, default=None, help='Output file location (if set, will also print)')
    args = parser.parse_args()

    config = {
        "url": args.url,
        "headless": args.headless,
        "dump_to": args.dump_to,
        "print": True,
    }

    pipeline = PipelineRegistry.get(args.pipeline)

    if not pipeline:
        ic(f"Error: Pipeline '{args.pipeline}' not found in registry")
        return

    try:
        ic(f"Running pipeline '{args.pipeline}' with URL:", config["url"])
        ic("Headless mode:", config["headless"])
        if config["dump_to"]:
            ic("Output will be saved to:", config["dump_to"])

        processed_data = await pipeline.run(url=config["url"], headless=config["headless"], dump_to=config["dump_to"])

        formatted_data = json.dumps(processed_data, indent=2, ensure_ascii=False)
        ic("Processing complete. Extracted data:")
        print(formatted_data)
        if config["dump_to"]:
            ic("Data also saved to:", config["dump_to"])

    except Exception as e:
        ic("Error during pipeline execution:", e)

    ic("Run completed.")


if __name__ == "__main__":
    asyncio.run(main())
