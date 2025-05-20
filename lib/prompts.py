translate_system = '''Translate flattened product data from a Chinese e-commerce platform into English,
maintaining the original structure and format.

# Task
Your task is to translate Chinese product data into English accurately. You will receive a list of
path-text pairs, where each pair consists of:
1. A "path" indicating the location of the data in the original structure
2. A "text" containing the Chinese content that needs to be translated

# CRITICAL REQUIREMENT
YOU MUST RETURN EXACTLY ONE TRANSLATION ITEM FOR EACH INPUT ITEM, even if you decide not to translate it.
The length of your "translations" array MUST EXACTLY MATCH the length of the input array. Do not skip any items.

# Guidelines
- Analyze each text value to determine if it should be translated
- Use appropriate product terminology in your translations
- Maintain the original meaning while making the translation natural in English
- If a text contains both Chinese and non-Chinese parts, only translate the Chinese parts
- For product codes and specifications with Chinese characters, translate only the Chinese words while
  preserving the structure and formatting

# Rules for Determining What Should NOT Be Translated
- URLs, links, image paths, or any web addresses (e.g., "https://", "www.")
- Pure product codes or SKUs without Chinese words (e.g., "A123B456C")
- Pure numeric values (e.g., "220V", "5V 2A")
- Currency values (e.g., "¥31.80", "USD 25")
- Email addresses
- Technical specifications that are standardized (e.g., "AC220-250V", "50/60HZ")
- Any text that consists solely of numbers, symbols, or Latin characters

# Special Translation Rules
- For product codes with Chinese characters or units (e.g., "K36-0.8米-黑"), translate only the Chinese words
  and units to their English equivalents (e.g., "K36-0.8m-Black") while preserving the code structure
- Preserve all numbers, dashes, and other formatting characters in the original position
- For measurements, convert Chinese units to appropriate English units (e.g., "米" → "m", "厘米" → "cm")

# Response Format
You MUST return a list in the "translations" field that contains EXACTLY ONE ITEM FOR EACH INPUT ITEM.
For every input item, include:
1. The original path
2. The original text
3. A boolean "should_translate" flag indicating if the text needs translation
4. The translated text (only when should_translate is true)

```
{
  "translations": [
    {
      "path": "product_title_main",
      "original_text": "多功能无线充电插座带USB快充插线板家用宿舍创意插排",
      "should_translate": true,
      "translated_text": "Multifunctional Wireless Charging Socket with USB Fast Charging Power Strip"
    },
    {
      "path": "url",
      "original_text": "https://detail.1688.com/offer/764286652699.html",
      "should_translate": false,
      "translated_text": null
    },
    {
      "path": "spec_variants.values[0][1]",
      "original_text": "K36-0.8米-黑",
      "should_translate": true,
      "translated_text": "K36-0.8m-Black"
    }
  ]
}
```

# IMPORTANT NOTES
- Your output MUST include EVERY item from the input, regardless of whether you translate it or not
- The order of items in your output should match the order in the input
- If "should_translate" is false, set "translated_text" to null
- DO NOT skip any items, even if they don't need translation

# Examples

## Input
```
[
  {"path": "product_title_main", "text": "多功能无线充电插座带USB快充插线板家用宿舍创意插排"},
  {"path": "product_title_second", "text": "带线接线板"},
  {"path": "price", "text": "¥31.80~¥51.801个起批"},
  {"path": "url", "text": "https://detail.1688.com/offer/764286652699.html"},
  {"path": "spec_variants.values[0][1]", "text": "K36-0.8米-黑"}
]
```

## Output
```
{
  "translations": [
    {
      "path": "product_title_main",
      "original_text": "多功能无线充电插座带USB快充插线板家用宿舍创意插排",
      "should_translate": true,
      "translated_text": "Multifunctional Wireless Charging Socket with USB Fast Charging Power Strip"
    },
    {
      "path": "product_title_second",
      "original_text": "带线接线板",
      "should_translate": true,
      "translated_text": "Wired Power Strip"
    },
    {
      "path": "price",
      "original_text": "¥31.80~¥51.801个起批",
      "should_translate": true,
      "translated_text": "¥31.80~¥51.80 Minimum Order: 1 piece"
    },
    {
      "path": "url",
      "original_text": "https://detail.1688.com/offer/764286652699.html",
      "should_translate": false,
      "translated_text": null
    },
    {
      "path": "spec_variants.values[0][1]",
      "original_text": "K36-0.8米-黑",
      "should_translate": true,
      "translated_text": "K36-0.8m-Black"
    }
  ]
}
```
'''

translate_user_template = '''I need you to translate the following flattened product data from Chinese to English.
Please follow the guidelines in the system prompt carefully. Remember to analyze each item and determine
whether it should be translated based on the rules.

CRITICAL: You MUST return ONE translation item for EACH input item, even if you decide not to translate it.
Your output must contain EXACTLY the same number of items as the input.

Product data to translate:
```
{data}
```

Return the translated data in the correct structured format, with ALL input items included in your response.'''

generate_system = '''

'''
