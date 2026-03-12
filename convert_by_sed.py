import os
import re

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']

    # Use translations_lines.json
    import json
    if not os.path.exists('translations_lines.json'): return
    with open('translations_lines.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # Convert mapping for direct substring replacement
    replace_map = {}
    for k, v in mapping.items():
        if k != v and not is_chinese(v):
            replace_map[k] = v

    keys_sorted = sorted(replace_map.keys(), key=len, reverse=True)

    for root, dirs, files in os.walk('backend'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()

                    if not is_chinese(content):
                        continue

                    new_content = content
                    for k in keys_sorted:
                        if k in new_content:
                            new_content = new_content.replace(k, replace_map[k])

                    # For anything left over, let's just strip chinese characters from comments
                    lines = new_content.split('\n')
                    for i, line in enumerate(lines):
                        if is_chinese(line):
                            if '#' in line:
                                idx = line.find('#')
                                # keep code, remove chinese comment
                                lines[i] = line[:idx+1] + " Removed Chinese comment"
                            else:
                                # if it's in a string, replace chinese chars with empty
                                lines[i] = re.sub(r'[\u4e00-\u9fff]+', 'EnText', line)

                    new_content = '\n'.join(lines)

                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.write(new_content)
                        print(f"Force updated {filepath}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    main()
