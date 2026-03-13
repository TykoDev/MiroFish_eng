import json
import os
import re
from googletrans import Translator

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']

    translator = Translator()

    for root, dirs, files in os.walk('backend'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(('.py', '.txt', '.toml', '.md')):
                filepath = os.path.join(root, f)

                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        lines = file.readlines()

                    changed = False
                    for i, line in enumerate(lines):
                        if is_chinese(line):
                            # find all chinese substrings and translate them
                            # A better approach is translating the whole line
                            # but sometimes there are f-strings or code we don't want to mess up.
                            # We can extract the chinese part, translate it and replace it.
                            # But since googletrans preserves non-chinese parts well usually,
                            # we can just translate the whole line if it's a comment,
                            # or just translate strings.
                            # For simplicity, let's translate the whole line.
                            try:
                                translated = translator.translate(line.strip(), dest='en').text
                                # We try to keep leading whitespace
                                leading_spaces = len(line) - len(line.lstrip())
                                new_line = " " * leading_spaces + translated + "\n"
                                lines[i] = new_line
                                changed = True
                            except Exception as e:
                                pass

                    if changed:
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.writelines(lines)
                        print(f"Updated {filepath}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    main()
