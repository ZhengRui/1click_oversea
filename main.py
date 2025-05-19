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
from lib.translate import translate_product


async def main():
    parser = argparse.ArgumentParser(description="Run product extraction pipeline.")
    parser.add_argument(
        '--pipeline', type=str, default='alibaba_1688', help='Pipeline name to use (default: alibaba_1688)'
    )
    parser.add_argument(
        '--url',
        type=str,
        help='Product URL to scrape',
        default='https://detail.1688.com/offer/764286652699.html',
    )
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--dump_to', type=str, default=None, help='Output file location (if set, will also print)')
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
        "print": True,
        "translate": args.translate,
        "translated_output": args.translated_output,
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

        # if config["translate"]:
        #     ic("Translating product data to English...")
        #     translated_data = await translate_product(processed_data)

        #     # Determine output file for translated data
        #     translated_output = config["translated_output"]
        #     if not translated_output and config["dump_to"]:
        #         # Create a filename for the translated output based on the original
        #         output_path = Path(config["dump_to"])
        #         translated_output = str(output_path.parent / f"{output_path.stem}_translated{output_path.suffix}")

        #     # Print and save translated data
        #     translated_formatted = json.dumps(translated_data, indent=2, ensure_ascii=False)
        #     ic("Translation complete:")
        #     print(translated_formatted)

        #     if translated_output:
        #         with open(translated_output, 'w', encoding='utf-8') as f:
        #             f.write(translated_formatted)
        #         ic("Translated data saved to:", translated_output)

        translated_data = json.load(open("data/example_product_data_translated.json", "r", encoding="utf-8"))
        formatted_translated_data = json.dumps(translated_data, indent=2, ensure_ascii=False)
        ic("Translated data:")
        print(formatted_translated_data)

        # Start a web server in the background
        import subprocess

        webserver = subprocess.Popen(["python", "-m", "http.server", "8000"])
        ic("Started web server on port 8000")

        # Open the page with Playwright (async API)
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto("http://localhost:8000/data/example_product_page.html")
            ic("Opened example product page in browser")
            print("Press Enter to close the browser and end the program...")
            # We need to use asyncio.get_event_loop().run_in_executor for blocking I/O operations in async context
            await asyncio.get_event_loop().run_in_executor(None, input, "")
            await browser.close()

        # Terminate the web server
        webserver.terminate()
        ic("Web server terminated")

    except Exception as e:
        ic("Error during pipeline execution:", e)

    ic("Run completed.")


if __name__ == "__main__":
    asyncio.run(main())
