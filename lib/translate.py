import json
import os
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from .prompts import translate_system, translate_user_template

load_dotenv(override=True)

proxy = os.getenv("http_proxy")
if proxy:
    client = httpx.AsyncClient(proxy=proxy)
else:
    client = httpx.AsyncClient()

model = OpenAIModel('gpt-4o-mini', provider=OpenAIProvider(http_client=client))

agent = Agent(model=model, system_prompt=translate_system, retries=3)


# Define translation status enum
class TranslationStatus(str, Enum):
    TRANSLATED = "translated"
    NOT_NEEDED = "not_needed"
    MISSED = "missed"


# Define Pydantic models for structured output
class TranslationItem(BaseModel):
    path: str
    original_text: str
    should_translate: bool
    translated_text: Optional[str] = None


class TranslationResponse(BaseModel):
    translations: List[TranslationItem]


def flatten_product_data(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Flatten a nested product data structure into a list of path and text pairs.

    Args:
        data: The product data dictionary

    Returns:
        A list of dictionaries with 'path' and 'text' keys
    """
    result = []

    def _flatten(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, (dict, list)):
                    _flatten(value, new_path)
                elif value is not None:
                    result.append({"path": new_path, "text": str(value)})
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                if isinstance(item, (dict, list)):
                    _flatten(item, new_path)
                elif item is not None:
                    result.append({"path": new_path, "text": str(item)})

    _flatten(data)
    return result


async def translate_flattened_data(
    flattened_data: List[Dict[str, str]], chunk_size: int = 50, max_passes: int = 3, progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Translate flattened product data with multiple passes to handle mismatches.

    Args:
        flattened_data: A list of dictionaries with 'path' and 'text' keys
        chunk_size: Number of items to translate in each chunk
        max_passes: Maximum number of passes to attempt for full translation
        progress_callback: Optional callback function for progress updates

    Returns:
        A list of dictionaries with 'path', 'text', and 'translation_status' keys
    """
    # Store translation results and tracking
    translations = {}
    status_map = {}  # Maps path to TranslationStatus

    # Start with all items pending
    pending_items = flattened_data.copy()
    total_items = len(flattened_data)

    print(f"Starting translation of {total_items} items with up to {max_passes} passes")

    # Initial progress report
    if progress_callback:
        progress_callback(
            {
                "stage": "translating",
                "status": "started",
                "total_items": total_items,
                "processed_items": 0,
                "percent": 0,
            }
        )

    # Process in multiple passes until everything is translated or max passes reached
    for pass_num in range(1, max_passes + 1):
        if not pending_items:
            print(f"All items translated after {pass_num-1} passes")
            break

        print(f"Pass {pass_num}/{max_passes}: Processing {len(pending_items)} items")

        # Items that remain untranslated after this pass
        new_pending_items = []

        # Process in chunks
        chunks = [pending_items[i : i + chunk_size] for i in range(0, len(pending_items), chunk_size)]

        # For progress reporting
        chunks_completed = 0
        total_chunks = len(chunks)

        for chunk_idx, chunk in enumerate(chunks):
            print(f"  - Chunk {chunk_idx+1}/{len(chunks)}: {len(chunk)} items")

            # Create a lookup dict for this chunk
            chunk_dict = {item["path"]: item for item in chunk}

            # Format chunk data as JSON string
            chunk_json = json.dumps(chunk, ensure_ascii=False, indent=2)

            # Create user prompt with the chunk data
            user_prompt = translate_user_template.format(data=chunk_json)

            # Use structured output with the agent
            result = await agent.run(user_prompt, output_type=TranslationResponse)

            # Process the results
            if result.output and hasattr(result.output, "translations"):
                # Track which paths were processed in the response
                processed_paths = set()

                # Process each returned translation
                for item in result.output.translations:
                    processed_paths.add(item.path)

                    if item.should_translate and item.translated_text:
                        # Store translated text and mark as translated
                        translations[item.path] = item.translated_text
                        status_map[item.path] = TranslationStatus.TRANSLATED
                    else:
                        # Use original text for items not needing translation
                        translations[item.path] = chunk_dict.get(item.path, {}).get("text", "")
                        status_map[item.path] = TranslationStatus.NOT_NEEDED

                # Find items that weren't returned by the model
                for path, item in chunk_dict.items():
                    if path not in processed_paths:
                        new_pending_items.append(item)

                print(
                    f"    - Processed: {len(processed_paths)}/{len(chunk)} items,"
                    f" {len(chunk) - len(processed_paths)} missing"
                )
            else:
                # If no valid response, retry the entire chunk in the next pass
                new_pending_items.extend(chunk)
                print("    - Failed to get valid translations for this chunk")

            # Update progress after each chunk
            chunks_completed += 1
            processed_count = len(translations)

            if progress_callback:
                progress_callback(
                    {
                        "stage": "translating",
                        "status": "in_progress",
                        "pass": pass_num,
                        "pass_progress": {
                            "current_chunk": chunks_completed,
                            "total_chunks": total_chunks,
                            "chunk_percent": int(chunks_completed / total_chunks * 100),
                        },
                        "total_items": total_items,
                        "processed_items": processed_count,
                        "percent": int(processed_count / total_items * 100),
                    }
                )

        # Update pending items for next pass
        pending_items = new_pending_items

        # Log progress
        processed_count = len(translations)
        print(
            f"  Pass {pass_num} completed: {processed_count}/{total_items} items processed"
            f" ({int(processed_count/total_items*100)}%)"
        )

        # Progress update after each pass
        if progress_callback:
            progress_callback(
                {
                    "stage": "translating",
                    "status": "pass_completed",
                    "pass": pass_num,
                    "total_passes": max_passes,
                    "total_items": total_items,
                    "processed_items": processed_count,
                    "percent": int(processed_count / total_items * 100),
                }
            )

    # For any remaining untranslated items after all passes, use original text and mark as missed
    for item in pending_items:
        translations[item["path"]] = item["text"]
        status_map[item["path"]] = TranslationStatus.MISSED

    # Reconstruct the result in the original order with translation status
    result = []
    for item in flattened_data:
        path = item["path"]
        result.append(
            {
                "path": path,
                "text": translations.get(path, item["text"]),
                "translation_status": status_map.get(path, TranslationStatus.MISSED),
            }
        )

    # Log translation statistics
    translated = sum(1 for item in result if item["translation_status"] == TranslationStatus.TRANSLATED)
    not_needed = sum(1 for item in result if item["translation_status"] == TranslationStatus.NOT_NEEDED)
    missed = sum(1 for item in result if item["translation_status"] == TranslationStatus.MISSED)

    print(f"Translation completed: {len(result)}/{total_items} total items")
    print(f"  - {translated} translated")
    print(f"  - {not_needed} not needing translation")
    print(f"  - {missed} missed after {max_passes} passes")

    # Final progress update
    if progress_callback:
        progress_callback(
            {
                "stage": "translating",
                "status": "completed",
                "total_items": total_items,
                "processed_items": total_items,
                "translated": translated,
                "not_needed": not_needed,
                "missed": missed,
                "percent": 100,
            }
        )

    return result


def rebuild_product_data(original_data: Dict[str, Any], translated_flat_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Rebuild the original data structure with translated values.

    Args:
        original_data: The original product data structure
        translated_flat_data: A list of dictionaries with 'path' and translated 'text' keys

    Returns:
        A dictionary with the same structure as original_data but with translated values
    """
    # Create a deep copy of the original data to avoid modifying it
    result = json.loads(json.dumps(original_data))

    # Create a map of path to translated text
    path_to_text = {item["path"]: item["text"] for item in translated_flat_data}

    def _update_value(obj: Union[Dict, List], path: str) -> None:
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, (dict, list)):
                    _update_value(value, current_path)
                elif current_path in path_to_text:
                    obj[key] = path_to_text[current_path]
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                if isinstance(item, (dict, list)):
                    _update_value(item, current_path)
                elif current_path in path_to_text:
                    obj[i] = path_to_text[current_path]

    _update_value(result, "")
    return result


async def translate_product_data(
    data: Dict[str, Any], chunk_size: int = 50, max_passes: int = 3, progress_callback=None
) -> Dict[str, Any]:
    """
    Translate product data from Chinese to English.

    Args:
        data: The product data dictionary
        chunk_size: Number of items to translate in each chunk
        max_passes: Maximum number of passes to attempt for full translation
        progress_callback: Optional callback function for progress updates

    Returns:
        A dictionary with the same structure as data but with translated values
    """
    # Flatten the product data
    flattened_data = flatten_product_data(data)

    # Translate the flattened data with multiple passes
    translated_data = await translate_flattened_data(flattened_data, chunk_size, max_passes, progress_callback)

    # Rebuild the original structure with translated values
    translated_product = rebuild_product_data(data, translated_data)

    return translated_product
