"""
Main script for using the Alibaba 1688 pipeline implementation.

This script fetches product data from Alibaba's 1688.com wholesale platform
using the registered alibaba_1688 pipeline.
"""

import argparse
import asyncio
import json
from pathlib import Path

from lib import PipelineRegistry
from lib.translate import translate_product_data


async def main():
    parser = argparse.ArgumentParser(description="Run product extraction pipeline.")
    parser.add_argument(
        '--pipeline', type=str, default='alibaba_1688', help='Pipeline name to use (default: alibaba_1688)'
    )
    parser.add_argument('--url', type=str, required=True, help='Product URL to scrape')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--dump_to', type=str, default=None, help='Output file location (if set, will also print)')
    parser.add_argument('--wait_for', type=int, default=10, help='Delay before returning HTML in seconds (default: 10)')
    parser.add_argument('--translate', action='store_true', help='Translate product data to English')
    parser.add_argument(
        '--translated_output',
        type=str,
        default=None,
        help='Output file for translated data (defaults to [original_filename]_translated.json if not specified)',
    )
    args = parser.parse_args()

    config = {
        "url": args.url,
        "headless": args.headless,
        "dump_to": args.dump_to,
        "wait_for": args.wait_for,
        "print": True,
        "translate": args.translate,
        "translated_output": args.translated_output,
    }

    pipeline = PipelineRegistry.get(args.pipeline)

    if not pipeline:
        print(f"Error: Pipeline '{args.pipeline}' not found in registry")
        return

    try:
        print(f"Running pipeline '{args.pipeline}' with URL:", config["url"])
        print("Headless mode:", config["headless"])
        print("Wait time:", config["wait_for"], "seconds")
        if config["dump_to"]:
            print("Output will be saved to:", config["dump_to"])

        # Update the delay_before_return_html in the run_config
        if pipeline.run_config and hasattr(pipeline.run_config, 'delay_before_return_html'):
            pipeline.run_config.delay_before_return_html = config["wait_for"]

        processed_data = await pipeline.run(url=config["url"], headless=config["headless"], dump_to=config["dump_to"])

        formatted_data = json.dumps(processed_data, indent=2, ensure_ascii=False)
        print("Processing complete. Extracted data:")
        print(formatted_data)
        if config["dump_to"]:
            print("Data also saved to:", config["dump_to"])

        # Translation step
        if config["translate"]:
            print("Translating product data to English...")
            translated_data = await translate_product_data(processed_data)

            # Determine output file for translated data
            translated_output = config["translated_output"]
            if not translated_output and config["dump_to"]:
                output_path = Path(config["dump_to"])
                translated_output = str(output_path.parent / f"{output_path.stem}_translated{output_path.suffix}")

            # Print and save translated data
            translated_formatted = json.dumps(translated_data, indent=2, ensure_ascii=False)
            print("Translation complete")
            print(translated_formatted)

            if translated_output:
                with open(translated_output, 'w', encoding='utf-8') as f:
                    f.write(translated_formatted)
                print("Translated data saved to:", translated_output)

    except Exception as e:
        print("Error during pipeline execution:", e)

    print("Run completed.")


if __name__ == "__main__":
    asyncio.run(main())
