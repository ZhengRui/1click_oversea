import asyncio
import json
import os
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

url = "https://detail.1688.com/offer/764286652699.html"
# url = "https://detail.1688.com/offer/865196865369.html"


# Process the spec variants table into a more usable format
def process_spec_variants(variants_data):
    if not variants_data or "headers" not in variants_data or "rows" not in variants_data:
        return None

    headers = [header.get("name", "") for header in variants_data.get("headers", [])]
    rows = variants_data.get("rows", [])

    # Create a list to store the processed variants data
    processed_variants = []

    # Process each row
    for row in rows:
        cells = row.get("cells", [])
        # Create a dictionary for this variant by combining headers with cell values
        variant_dict = {}

        # Extract image URL from style attribute if available
        if "image_url" in row and row["image_url"]:
            # Extract the URL from background-image: url("URL");
            style = row["image_url"]
            url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if url_match:
                variant_dict["image_url"] = url_match.group(1)

        # Zip headers with cell values and create a dictionary
        for i, header in enumerate(headers):
            if i < len(cells) and "value" in cells[i]:
                variant_dict[header] = cells[i]["value"]
            else:
                variant_dict[header] = ""

        # Add the variant dictionary to our processed_variants list
        processed_variants.append(variant_dict)

    return processed_variants


# Process the product images data into a more usable format
def process_product_images(images_data):
    if not images_data or "images" not in images_data:
        return None

    image_list = []

    for image_wrapper in images_data.get("images", []):
        image_info = {}

        # Extract the image URL
        if "image_url" in image_wrapper:
            image_info["url"] = image_wrapper["image_url"]

        # Extract the image index
        if "index" in image_wrapper:
            image_info["index"] = image_wrapper["index"]

        # Check if this is a video (by presence of video icon source)
        if "video_icon_src" in image_wrapper and image_wrapper["video_icon_src"]:
            image_info["is_video"] = True
        else:
            image_info["is_video"] = False

        image_list.append(image_info)

    # Sort images by index
    image_list.sort(key=lambda x: int(x.get("index", "0")) if x.get("index", "0").isdigit() else 0)

    return image_list


# Process the product detail content into a more usable format
def process_product_details(details_data):
    result = {}

    # Process detail images
    if details_data and "detail_images" in details_data and details_data["detail_images"]:
        detail_images = []

        for image_data in details_data.get("detail_images", []):
            image_info = {}

            # For loaded images, the src will have the actual image
            # For lazy images, use data-lazyload-src if available, otherwise use src (placeholder)
            if "actual_image_src" in image_data and image_data["actual_image_src"]:
                image_info["url"] = image_data["actual_image_src"]
            elif "placeholder_src" in image_data and image_data["placeholder_src"]:
                # Check if this is a placeholder or an actual loaded image
                if "lazyload.png" not in image_data["placeholder_src"]:
                    image_info["url"] = image_data["placeholder_src"]
                else:
                    # Skip pure placeholder images with no actual image URL
                    continue
            else:
                continue  # Skip if no URL is available

            detail_images.append(image_info)

        result["images"] = detail_images

    # Keep the original title if available
    if details_data and "title" in details_data:
        result["title"] = details_data["title"]

    return result


async def main():
    browser_config = BrowserConfig(
        headless=False,
        verbose=True,
        use_managed_browser=True,
        browser_type="chromium",
        user_data_dir="/Users/zerry/Work/Projects/funs/1click_oversea/data/1688_profile",
    )

    extraction_strategy = JsonCssExtractionStrategy(
        {
            "name": "ProductDetails",
            "baseSelector": "body",
            "fields": [
                {
                    "name": "product_title_main",
                    "selector": ".title-first-column .title-text",
                    "type": "text",
                },
                {
                    "name": "product_title_second",
                    "selector": ".title-second-column .title-text",
                    "type": "text",
                },
                {
                    "name": "sales_count",
                    "selector": ".title-sale-column .title-info-number",
                    "type": "text",
                },
                {
                    "name": "evaluation_count",
                    "selector": ".title-info-number[data-real-number]",
                    "type": "text",
                },
                {
                    "name": "logistics",
                    "selector": ".logistics-city",
                    "type": "text",
                },
                {
                    "name": "head_attributes",
                    "selector": ".cpv-item",
                    "type": "nested_list",
                    "fields": [
                        {
                            "name": "name",
                            "selector": ".cpv-item-info-subtitle",
                            "type": "text",
                        },
                        {
                            "name": "value",
                            "selector": ".cpv-item-info-title",
                            "type": "text",
                        },
                    ],
                },
                {
                    "name": "filter_data",
                    "selector": ".filters",
                    "type": "nested",
                    "fields": [
                        {
                            "name": "search",
                            "type": "nested",
                            "selector": ".search-wrapper",
                            "fields": [
                                {"name": "label", "selector": ".label", "type": "text"},
                                {
                                    "name": "placeholder",
                                    "selector": "input",
                                    "type": "attribute",
                                    "attribute": "placeholder",
                                },
                                {"name": "button_text", "selector": ".next-search-btn-text", "type": "text"},
                            ],
                        },
                        {
                            "name": "filters",
                            "type": "nested_list",
                            "selector": ".radio-selector-bar",
                            "fields": [
                                {"name": "category", "selector": ".label-content", "type": "text"},
                                {
                                    "name": "options",
                                    "selector": ".btn-selector-item .next-btn-helper",
                                    "type": "list",
                                    "fields": [{"name": "option", "type": "text"}],
                                },
                                {"name": "default_selected", "selector": ".selected .next-btn-helper", "type": "text"},
                            ],
                        },
                        {
                            "name": "other_specs",
                            "type": "nested_list",
                            "selector": ".radio-props-list-item",
                            "fields": [
                                {"name": "spec_name", "selector": "spn", "type": "text"},
                                {"name": "spec_value", "selector": "span", "type": "text"},
                            ],
                        },
                    ],
                },
                {
                    "name": "spec_variants",
                    "selector": ".selector-table",
                    "type": "nested",
                    "fields": [
                        {
                            "name": "headers",
                            "selector": "th.next-table-header-node",
                            "type": "list",
                            "fields": [{"name": "name", "type": "text"}],
                        },
                        {
                            "name": "rows",
                            "selector": ".next-table-body tr",
                            "type": "nested_list",
                            "fields": [
                                {
                                    "name": "image_url",
                                    "selector": "td:first-child .od-gyp-pc-sku-selection-sku",
                                    "type": "attribute",
                                    "attribute": "style",
                                    "default": "",
                                },
                                {
                                    "name": "cells",
                                    "selector": "td",
                                    "type": "list",
                                    "fields": [{"name": "value", "type": "text"}],
                                },
                            ],
                        },
                    ],
                },
                {
                    "name": "body_attributes",
                    "selector": ".od-pc-attribute",
                    "type": "nested",
                    "fields": [
                        {
                            "name": "title",
                            "selector": ".offer-title-wrapper",
                            "type": "attribute",
                            "attribute": "data-title",
                        },
                        {
                            "name": "attributes",
                            "selector": ".offer-attr-item",
                            "type": "nested_list",
                            "fields": [
                                {"name": "name", "selector": ".offer-attr-item-name", "type": "text"},
                                {"name": "value", "selector": ".offer-attr-item-value", "type": "text"},
                            ],
                        },
                    ],
                },
                {
                    "name": "product_images",
                    "selector": ".img-list-wrapper",
                    "type": "nested",
                    "fields": [
                        {
                            "name": "images",
                            "selector": ".detail-gallery-turn-wrapper",
                            "type": "nested_list",
                            "fields": [
                                {
                                    "name": "image_url",
                                    "selector": ".detail-gallery-img",
                                    "type": "attribute",
                                    "attribute": "src",
                                },
                                {
                                    "name": "index",
                                    "selector": ".detail-gallery-img",
                                    "type": "attribute",
                                    "attribute": "ind",
                                },
                                {
                                    "name": "video_icon_src",
                                    "selector": ".video-icon",
                                    "type": "attribute",
                                    "attribute": "src",
                                    "default": "",
                                },
                            ],
                        }
                    ],
                },
                {
                    "name": "product_details",
                    "selector": ".detail-desc-module",
                    "type": "nested",
                    "fields": [
                        {
                            "name": "title",
                            "selector": ".offer-title-wrapper",
                            "type": "attribute",
                            "attribute": "data-title",
                            "default": "",
                        },
                        {
                            "name": "detail_images",
                            "selector": "img.desc-img-no-load, img.desc-img-loaded",
                            "type": "nested_list",
                            "fields": [
                                {"name": "placeholder_src", "type": "attribute", "attribute": "src"},
                                {"name": "actual_image_src", "type": "attribute", "attribute": "data-lazyload-src"},
                            ],
                        },
                    ],
                },
            ],
        }
    )

    # Extract selectors properly, handling both direct selectors and nested fields
    selectors = []

    # Helper function to recursively extract all selectors from the schema
    def extract_selectors(field_list, parent_selector=""):
        for field in field_list:
            if "selector" in field:
                # If there's a parent selector, combine them properly for nested elements
                if parent_selector:
                    # For attribute selectors, we still need the element itself highlighted
                    selector = f"{parent_selector} {field['selector']}"
                else:
                    selector = field["selector"]

                selectors.append(selector)

            # Process nested fields recursively
            if "fields" in field:
                # Determine the correct parent for the nested fields
                new_parent = ""
                if "selector" in field:
                    new_parent = field["selector"] if not parent_selector else f"{parent_selector} {field['selector']}"
                elif parent_selector:
                    new_parent = parent_selector

                extract_selectors(field["fields"], new_parent)

    # Start the extraction process
    extract_selectors(extraction_strategy.schema["fields"])

    # Add additional selectors of interest
    additional_selectors = []
    selectors.extend(additional_selectors)

    hover_elements = [".cpv-content"]

    # Load external JavaScript files
    base_dir = Path(__file__).parent.parent

    with open(base_dir / "utils" / "simHover.js", "r") as f:
        hover_function = f.read()

    with open(base_dir / "utils" / "highlight.js", "r") as f:
        highlight_function = f.read()

    # Create scripts to use our external functions
    hover_script = f"""
    // Load hover functionality
    {hover_function}
    // Call with our selectors
    expandHoverElements({json.dumps(hover_elements)});
    """

    highlight_script = f"""
    // Load highlight functionality
    {highlight_function}
    // Call with our selectors
    highlightElements({json.dumps(selectors)});
    """

    run_config = CrawlerRunConfig(
        wait_for="css:div#detailContentContainer",
        delay_before_return_html=10,
        js_code=[hover_script, highlight_script],
        extraction_strategy=extraction_strategy,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

        if result.success:
            if result.extracted_content:
                try:
                    extracted_data = json.loads(result.extracted_content)

                    # Post-process the data to clean up and restructure
                    if isinstance(extracted_data, list):
                        for page_data in extracted_data:
                            # Combine the title parts if both are present
                            if "product_title_main" in page_data and "product_title_second" in page_data:
                                print("Combining title parts")
                                page_data["full_title"] = (
                                    f"{page_data['product_title_main']}{page_data['product_title_second']}"
                                )

                            # Clean up filter options data
                            if "filter_data" in page_data and "filters" in page_data["filter_data"]:
                                for filter_category in page_data["filter_data"]["filters"]:
                                    if "options" in filter_category and isinstance(filter_category["options"], list):
                                        # Extract just the text values from the list of option objects
                                        option_values = []
                                        for option_obj in filter_category["options"]:
                                            if isinstance(option_obj, dict) and "option" in option_obj:
                                                option_values.append(option_obj["option"])
                                        filter_category["options"] = option_values

                            # Process spec variants data
                            if "spec_variants" in page_data:
                                processed_variants = process_spec_variants(page_data["spec_variants"])
                                if processed_variants:
                                    page_data["spec_variants"] = processed_variants

                            # Process product images data
                            if "product_images" in page_data:
                                processed_images = process_product_images(page_data["product_images"])
                                if processed_images:
                                    page_data["product_images"] = processed_images

                            # Process product details data
                            if "product_details" in page_data:
                                processed_details = process_product_details(page_data["product_details"])
                                if processed_details:
                                    page_data["product_details"] = processed_details

                    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print("Failed to parse extracted content as JSON. Raw content:")
                    print(result.extracted_content)
                except TypeError:
                    print("Extracted content is not string or bytes-like object for JSON parsing.")
                    print(result.extracted_content)
            else:
                print("No extracted content returned.")
        else:
            print(f"Crawler run failed. Error: {result.error_message}")

        print("Crawler run completed.")


if __name__ == "__main__":
    asyncio.run(main())
