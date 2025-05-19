"""
Alibaba 1688 product page extraction pipeline.

This module handles extraction of product data from Alibaba's 1688.com wholesale platform.
It provides configurable slices, post-processors, and pipeline registration for structured data extraction.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict

from crawl4ai.async_configs import CrawlerRunConfig

from ..pipeline import Pipeline
from ..registry import PipelineRegistry
from ..slice import Slice

# Post processor functions for individual slices


def process_spec_variants(variants_data):
    """Process spec variants data into a more usable format."""
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


def process_product_images(images_data):
    """Process product images data into a more usable format."""
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


def process_product_details(details_data):
    """Process product details into a more usable format."""
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


def process_filter_data(filter_data):
    """Process filter data into a more usable format."""
    if not filter_data:
        return None

    # Process options in filters
    if "filters" in filter_data and filter_data["filters"]:
        for filter_category in filter_data["filters"]:
            if "options" in filter_category and isinstance(filter_category["options"], list):
                # Extract just the text values from the list of option objects
                option_values = []
                for option_obj in filter_category["options"]:
                    if isinstance(option_obj, dict) and "option" in option_obj:
                        option_values.append(option_obj["option"])
                filter_category["options"] = option_values

    return filter_data


def process_sku_options(sku_data_list):
    """Process SKU options for multiple tables/styles."""
    if not sku_data_list or not isinstance(sku_data_list, list):
        return None
    result = []
    for sku_data in sku_data_list:
        category_name = sku_data.get("category_name")
        options = []
        # Style 1: color/image style (has image_style field)
        if "options" in sku_data and sku_data["options"] and "image_style" in sku_data["options"][0]:
            for option in sku_data["options"]:
                opt = {}
                if "title" in option:
                    opt["title"] = option["title"]
                if "image_style" in option and option["image_style"]:
                    style = option["image_style"]
                    url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                    if url_match:
                        opt["image_url"] = url_match.group(1)
                options.append(opt)
        # Style 2: spec/price/stock style (has sku_item_options field)
        elif "sku_item_options" in sku_data:
            for option in sku_data["sku_item_options"]:
                opt = {}
                if "name" in option:
                    opt["title"] = option["name"]
                if "price" in option:
                    opt["price"] = option["price"]
                if "stock" in option:
                    opt["stock"] = option["stock"]
                options.append(opt)
        result.append({"category_name": category_name, "options": options})
    return result


def merge_title(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process the entire 1688 product data after extraction.
    This handles cross-slice operations like combining titles.
    """
    # Don't modify the original data
    result = data.copy()

    # Combine the title parts if both are present
    if "product_title_main" in result and "product_title_second" in result:
        result["full_title"] = f"{result['product_title_main']}{result['product_title_second']}"

    return result


def process_package_details(table_data):
    """Process the package details table into a list of dicts with headers as keys."""
    if not table_data or "headers" not in table_data or "rows" not in table_data:
        return None

    headers = [header.get("name", "") for header in table_data.get("headers", [])]
    rows = table_data.get("rows", [])
    processed = []
    for row in rows:
        cells = row.get("cells", [])
        row_dict = {}
        for i, header in enumerate(headers):
            if i < len(cells) and "value" in cells[i]:
                row_dict[header] = cells[i]["value"]
            else:
                row_dict[header] = ""
        processed.append(row_dict)
    return processed


# Slice configurations for 1688 product pages
SLICES_CONFIG = [
    {"name": "product_title_main", "selector": ".title-first-column .title-text", "type": "text"},
    {"name": "product_title_second", "selector": ".title-second-column .title-text", "type": "text"},
    {"name": "sales_count", "selector": ".title-sale-column .title-info-number", "type": "text"},
    {"name": "evaluation_count", "selector": ".title-info-number[data-real-number]", "type": "text"},
    {"name": "price", "selector": ".price-content .price-column", "type": "text"},
    {"name": "logistics", "selector": ".logistics-city", "type": "text"},
    {
        "name": "sku_options",
        "selector": ".sku-module-wrapper",
        "type": "nested_list",
        "post_processor": process_sku_options,
        "fields": [
            {
                "name": "category_name",
                "selector": ".sku-prop-module-name",
                "type": "text",
                "default": "",
            },
            # Style 1: color/image style
            {
                "name": "options",
                "selector": ".prop-item-wrapper .prop-item",
                "type": "nested_list",
                "fields": [
                    {"name": "title", "selector": ".prop-name", "type": "text", "default": ""},
                    {
                        "name": "image_style",
                        "selector": ".prop-img",
                        "type": "attribute",
                        "attribute": "style",
                        "default": "",
                    },
                ],
            },
            # Style 2: spec/price/stock style
            {
                "name": "sku_item_options",
                "selector": ".sku-item-wrapper",
                "type": "nested_list",
                "fields": [
                    {"name": "name", "selector": ".sku-item-name", "type": "text", "default": ""},
                    {"name": "price", "selector": ".discountPrice-price", "type": "text", "default": ""},
                    {"name": "stock", "selector": ".sku-item-sale-num", "type": "text", "default": ""},
                ],
            },
        ],
    },
    {
        "name": "head_attributes",
        "selector": ".cpv-item",
        "type": "nested_list",
        "fields": [
            {"name": "name", "selector": ".cpv-item-info-subtitle", "type": "text"},
            {"name": "value", "selector": ".cpv-item-info-title", "type": "text"},
        ],
    },
    {
        "name": "filter_data",
        "selector": ".filters",
        "type": "nested",
        "post_processor": process_filter_data,
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
        "post_processor": process_spec_variants,
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
                    {"name": "cells", "selector": "td", "type": "list", "fields": [{"name": "value", "type": "text"}]},
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
        "post_processor": process_product_images,
        "fields": [
            {
                "name": "images",
                "selector": ".detail-gallery-turn-wrapper",
                "type": "nested_list",
                "fields": [
                    {"name": "image_url", "selector": ".detail-gallery-img", "type": "attribute", "attribute": "src"},
                    {"name": "index", "selector": ".detail-gallery-img", "type": "attribute", "attribute": "ind"},
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
        "post_processor": process_product_details,
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
    {
        "name": "package_details",
        "selector": ".od-pc-offer-cross .od-pc-offer-table table",
        "type": "nested",
        "post_processor": process_package_details,
        "fields": [
            {
                "name": "headers",
                "selector": "thead th",
                "type": "list",
                "fields": [{"name": "name", "type": "text"}],
            },
            {
                "name": "rows",
                "selector": "tbody tr",
                "type": "nested_list",
                "fields": [
                    {
                        "name": "cells",
                        "selector": "td",
                        "type": "list",
                        "fields": [{"name": "value", "type": "text"}],
                    }
                ],
            },
        ],
    },
]

# Comprehensive pipeline configuration for 1688 product pages
CONFIG = {
    "browser": {
        # "headless": False,
        # "verbose": True,
        "use_managed_browser": True,
        "browser_type": "chromium",
        "user_data_dir": "/Users/zerry/Work/Projects/funs/1click_oversea/data/1688_profile",
    },
    "run": {
        "wait_for": "css:div#detailContentContainer",
        "delay_before_return_html": 10,
        "js_code": [],  # JS code will be added at runtime
    },
    "slices": SLICES_CONFIG,
}


def get_js_scripts(base_dir, selectors):
    """Generate the JavaScript scripts for hover and highlighting."""
    # Set up hover and highlight functionality
    hover_elements = [".cpv-content"]

    # Load external JavaScript files for hover and highlighting
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

    return [hover_script, highlight_script]


# Create and register the 1688 pipeline
@PipelineRegistry.register_pipeline(name="alibaba_1688")
def create_alibaba_pipeline():
    """Create and return the Alibaba 1688 product page pipeline."""
    # First create the pipeline with initial configuration
    pipeline = Pipeline(name="Alibaba1688ProductPipeline", configs=CONFIG, post_processor=merge_title)

    # Get the base directory for loading script files
    base_dir = Path(__file__).parent.parent.parent

    # Get the selectors from the pipeline
    selectors = pipeline.selectors

    # Generate the JS scripts
    js_scripts = get_js_scripts(base_dir, selectors)

    # Update the run_config with the JS scripts
    pipeline.run_config.js_code = js_scripts

    return pipeline
