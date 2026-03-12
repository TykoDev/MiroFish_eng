import os
import json

def main():
    with open('translations_completed.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # filter mapping to only contain items where translation is different and doesn't contain chinese
    import re
    def is_chinese(text):
        return re.search(r'[\u4e00-\u9fff]', text) is not None

    valid_mapping = {}
    for k, v in mapping.items():
        if k != v and v and not is_chinese(v):
            valid_mapping[k] = v

    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']
    for root, dirs, files in os.walk('backend'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()

                # Simple replacement for now. Since strings in translation map are exactly the token strings.
                # Actually, replacing exactly might cause issues with substring replacements.
                # Let's sort keys by length descending so longer strings get replaced first.
                keys_sorted = sorted(valid_mapping.keys(), key=len, reverse=True)

                new_content = content
                for k in keys_sorted:
                    if k in new_content:
                        new_content = new_content.replace(k, valid_mapping[k])

                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"Updated {filepath}")

if __name__ == '__main__':
    main()
