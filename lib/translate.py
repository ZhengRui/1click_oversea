import json
import os
from typing import Any, Dict, Optional, Tuple

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from .prompts import translate_system

load_dotenv(override=True)

proxy = os.getenv("http_proxy")
if proxy:
    client = httpx.AsyncClient(proxy=proxy)
else:
    client = httpx.AsyncClient()

model = OpenAIModel('gpt-4o-mini', provider=OpenAIProvider(http_client=client))

agent = Agent(model=model, system_prompt=translate_system)


def split_product_data(product_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Split product data into parts that need translation and parts that don't.

    Args:
        product_data (Dict[str, Any]): The complete product data dictionary

    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: A tuple containing:
            - Dictionary of data that needs translation
            - Dictionary of data that doesn't need translation
    """
    # Make a deep copy to avoid modifying the original data
    translatable_data = {}
    non_translatable_data = {}

    # Top-level keys that don't need translation at all
    fully_non_translatable_keys = {'product_images', 'url'}

    # Process each key in the product data
    for key, value in product_data.items():
        if key in fully_non_translatable_keys:
            # These keys don't need any translation
            non_translatable_data[key] = value
        elif key == 'product_details':
            # Special handling for product_details
            if isinstance(value, dict):
                translatable_detail = {}
                non_translatable_detail = {}

                # Only title needs translation in product_details
                if 'title' in value:
                    translatable_detail['title'] = value['title']

                # Images don't need translation
                if 'images' in value:
                    non_translatable_detail['images'] = value['images']

                # Add to respective dictionaries if they have content
                if translatable_detail:
                    translatable_data['product_details'] = translatable_detail
                if non_translatable_detail:
                    non_translatable_data['product_details'] = non_translatable_detail
            else:
                # If it's not a dict, default to translatable
                translatable_data[key] = value
        else:
            # All other keys need translation
            translatable_data[key] = value

    return translatable_data, non_translatable_data


def merge_product_data(translated_data: Dict[str, Any], non_translatable_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge the translated data with the non-translatable data to create a complete product data.

    Args:
        translated_data (Dict[str, Any]): The translated part of the product data
        non_translatable_data (Dict[str, Any]): The non-translatable part of the product data

    Returns:
        Dict[str, Any]: Complete merged product data
    """
    # Start with the translated data
    merged_data = {**translated_data}

    # Merge non-translatable top-level keys
    for key, value in non_translatable_data.items():
        if key not in merged_data:
            # If the key doesn't exist in merged_data, add it directly
            merged_data[key] = value
        elif key == 'product_details' and isinstance(value, dict) and isinstance(merged_data.get(key), dict):
            # Special handling for product_details
            # Merge the images from non-translatable with the translated title
            merged_data[key] = {**merged_data[key], **value}
        # For other keys that exist in both, the translated version has priority

    return merged_data


class TranslatedData(BaseModel):
    """
    A Pydantic model that represents the translated data.
    This model acts as both a validator and type definition.
    """

    data: Dict[str, Any] = Field(description="The translated data with the same structure as the original")


async def translate_data(data_to_translate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate the given data from Chinese to English.

    Args:
        data_to_translate (Dict[str, Any]): The data to translate

    Returns:
        Dict[str, Any]: The translated data
    """
    # Convert to JSON string for the prompt
    data_json = json.dumps(data_to_translate, ensure_ascii=False, indent=2)

    # Create the prompt
    user_prompt = f"Please translate the following product data from Chinese to English:\n\n```json\n{data_json}\n```"

    # Use the agent to get a structured response
    result = await agent.run(user_prompt, output_type=TranslatedData)

    # Return the validated data
    return result.data


async def translate_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate a product from Chinese to English.

    Args:
        product_data (Dict[str, Any]): The complete product data

    Returns:
        Dict[str, Any]: The translated product data
    """
    # Split the data
    translatable, non_translatable = split_product_data(product_data)

    # Translate the translatable part
    translated_data = await translate_data(translatable)

    # Merge the data back together
    complete_data = merge_product_data(translated_data, non_translatable)

    return complete_data
