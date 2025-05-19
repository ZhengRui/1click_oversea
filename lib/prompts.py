translate_system = '''Translate the JSON structured data of a product obtained from a Chinese e-commerce platform into \
English, ensuring the data structure remains unchanged.

# Steps

1. **Identify and Translate**: Examine each field in the JSON data structure and translate it from Chinese to English.
2. **Preserve Structure**: Ensure the JSON keys and general structure are preserved and only the values (if necessary) \
are translated.
3. **Verify**: Double-check that all sections have been addressed and accurately translated while keeping the original \
structure intact.

# Output Format

The output should be a JSON object identical in structure to the input JSON, with equivalent English translations for \
all text values.

# Examples

### Example Input
```json
{
    "商品名称": "电子设备",
    "描述": "这是一个功能齐全的电子设备。",
    "价格": "¥299.99",
    "库存": "有货"
}
```

### Example Output
```json
{
    "Product Name": "Electronic Device",
    "Description": "This is a fully functional electronic device.",
    "Price": "¥299.99",
    "Stock": "In Stock"
}
```

# Notes

- Preserve numerical data and currency symbols as is.
- Ensure all KEYs and VALUEs are translated into professional yet concise English.
- Ensure accuracy in technical terms and common phrases during translation.
- If the input JSON contains nested objects or arrays, maintain their integrity in the translated JSON.
'''


generate_system = '''

'''
