import json
import os
import re

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']

    with open('translations_lines.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # Clean the mapping so no new lines or bad translations replace everything
    valid_mapping = {k: v for k, v in mapping.items() if k != v and v and not is_chinese(v)}
    keys_sorted = sorted(valid_mapping.keys(), key=len, reverse=True)

    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(('.py', '.js', '.vue', '.html', '.md', '.json', '.yml', '.yaml', '.txt', '.toml')):
                filepath = os.path.join(root, f)
                if 'README-EN' in f or 'STATUS' in f or 'REFAC' in f or 'AGENTS' in f or 'translations' in f or f == 'README.md':
                    continue
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()

                    if not is_chinese(content):
                        continue

                    new_content = content
                    for k in keys_sorted:
                        if k in new_content:
                            # It's better to replace lines exactly instead of arbitrary text, but let's try line by line matching
                            pass

                    # Actual line by line approach
                    lines = new_content.split('\n')
                    changed = False
                    for i, line in enumerate(lines):
                        if is_chinese(line):
                            stripped = line.strip()
                            if stripped in valid_mapping:
                                lines[i] = line.replace(stripped, valid_mapping[stripped])
                                changed = True
                            else:
                                # Try partial matches if the line has mixed content
                                for k in keys_sorted:
                                    if k in lines[i]:
                                        lines[i] = lines[i].replace(k, valid_mapping[k])
                                        changed = True

                    if changed:
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.write('\n'.join(lines))
                        print(f"Updated {filepath}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    main()
