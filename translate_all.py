import os
import re

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']
    files_to_process = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(('.py', '.js', '.vue', '.html', '.md', '.json', '.yml', '.yaml', '.txt', '.toml')):
                filepath = os.path.join(root, f)
                files_to_process.append(filepath)

    with open('translations_completed.json', 'r', encoding='utf-8') as f:
        import json
        mapping = json.load(f)

    # Sort keys by length so longer replacements happen first
    valid_mapping = {k: v for k, v in mapping.items() if k != v and v and not is_chinese(v)}
    keys_sorted = sorted(valid_mapping.keys(), key=len, reverse=True)

    for filepath in files_to_process:
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()

            if not is_chinese(content):
                continue

            new_content = content
            for k in keys_sorted:
                if k in new_content:
                    new_content = new_content.replace(k, valid_mapping[k])

            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f"Updated {filepath}")
        except Exception as e:
            pass

if __name__ == '__main__':
    main()
