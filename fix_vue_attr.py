import os
import re

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']
    for root, dirs, files in os.walk('frontend'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith('.vue'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        lines = file.readlines()

                    changed = False
                    for i, line in enumerate(lines):
                        # Fix broken placeholder="// EN_Comment
                        if 'placeholder="// EN_Comment' in line and '"' not in line.split('placeholder="')[1]:
                            lines[i] = line.replace('placeholder="// EN_Comment', 'placeholder="EN_Comment"')
                            changed = True
                        if 'placeholder="<!-- EN_Comment -->' in line:
                            lines[i] = line.replace('placeholder="<!-- EN_Comment -->"', 'placeholder="EN_Comment"')
                            changed = True

                    if changed:
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.writelines(lines)
                        print(f"Fixed {filepath}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    main()
