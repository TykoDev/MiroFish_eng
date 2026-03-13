import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from googletrans import Translator

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def translate_batch(texts):
    if not texts: return []
    translator = Translator()
    res_list = []
    for t in texts:
        try:
            if not is_chinese(t):
                res_list.append(t)
            else:
                res = translator.translate(t, dest='en')
                res_list.append(res.text)
        except Exception as e:
            # Fallback to original text if translation fails
            res_list.append(t)
    return res_list

def main():
    with open('translations.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    if os.path.exists('translations_completed.json'):
        with open('translations_completed.json', 'r', encoding='utf-8') as f:
            completed = json.load(f)
            mapping.update(completed)

    pending = [k for k, v in mapping.items() if not v or v == k and is_chinese(k)]
    print(f"Total pending: {len(pending)}")

    batch_size = 50
    batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(translate_batch, batches)

        idx = 0
        for batch_res in results:
            for translated in batch_res:
                mapping[pending[idx]] = translated
                idx += 1
            print(f"Processed batch, {idx}/{len(pending)}")
            with open('translations_completed.json', 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
