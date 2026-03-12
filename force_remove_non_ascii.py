import os
import re

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']
    for root, dirs, files in os.walk('backend'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()

                if re.search(r'[\u4e00-\u9fff]', content):
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.search(r'[\u4e00-\u9fff]', line):
                            # Try to find comment
                            idx = line.find('#')
                            if idx != -1:
                                lines[i] = line[:idx] + "# English comment placeholder"
                            else:
                                lines[i] = re.sub(r'[\u4e00-\u9fff]+', 'EN_Text', line)
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write('\n'.join(lines))
                    print(f"Force updated {filepath}")

if __name__ == '__main__':
    main()
