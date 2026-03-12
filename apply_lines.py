import os
import json

def main():
    with open('translations_lines.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # filter mapping to only contain items where translation is different and doesn't contain chinese
    import re
    def is_chinese(text):
        return re.search(r'[\u4e00-\u9fff]', text) is not None

    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(('.py', '.js', '.vue', '.html', '.md', '.json', '.yml', '.yaml', '.txt', '.toml')):
                filepath = os.path.join(root, f)
                # Skip markdown docs, but we'll do root config and others
                if 'README-EN' in f or 'STATUS' in f or 'REFAC' in f or 'AGENTS' in f or 'translations' in f or 'test_trans' in f or f == 'README.md':
                    continue

                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        lines = file.readlines()

                    changed = False
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if is_chinese(stripped) and stripped in mapping:
                            new_val = mapping[stripped]
                            # Simple replacement to keep whitespace indentation intact
                            if not is_chinese(new_val) and new_val != stripped:
                                lines[i] = line.replace(stripped, new_val)
                                changed = True

                    if changed:
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.writelines(lines)
                        print(f"Updated {filepath}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    main()
