import json
import os
import sys
import re
from googletrans import Translator

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def translate_safe(text):
    try:
        if not is_chinese(text):
            return text
        translator = Translator()
        return translator.translate(text, dest='en').text
    except Exception as e:
        return text

def main():
    if not os.path.exists('translations_completed.json'):
        with open('translations.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    else:
        with open('translations_completed.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)

    # Let's count how many are missing translation
    pending = [k for k, v in mapping.items() if v == "" or v == k]
    print(f"Total pending: {len(pending)}")

    # Process 10 items
    for k in pending[:10]:
        t = translate_safe(k)
        mapping[k] = t
        print(f"Translated: {k[:20]} -> {t[:20]}")

    with open('translations_completed.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
