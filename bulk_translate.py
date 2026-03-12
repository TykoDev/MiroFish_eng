import json
import os
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from googletrans import Translator

def translate_batch(texts):
    if not texts: return []
    try:
        translator = Translator()
        # googletrans bulk translate works best with lists
        res = translator.translate(texts, dest='en')
        return [r.text for r in res]
    except Exception as e:
        print(f"Batch translate failed: {e}")
        return texts

def main():
    with open('translations.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    if os.path.exists('translations_completed.json'):
        with open('translations_completed.json', 'r', encoding='utf-8') as f:
            completed = json.load(f)
            mapping.update(completed)

    pending = [k for k, v in mapping.items() if not v or v == k]
    print(f"Total pending: {len(pending)}")

    batch_size = 50
    batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(translate_batch, batches)

        idx = 0
        for batch_res in results:
            for translated in batch_res:
                mapping[pending[idx]] = translated
                idx += 1

    with open('translations_completed.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print("Translation completed.")

if __name__ == '__main__':
    main()
