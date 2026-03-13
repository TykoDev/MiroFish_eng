import os
import sys

def contains_non_ascii(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if not line.isascii():
                    return True
    except Exception as e:
        return False
    return False

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(('.py', '.js', '.vue', '.html', '.md', '.json', '.yml', '.yaml', '.txt', '.toml')):
                filepath = os.path.join(root, f)
                if contains_non_ascii(filepath):
                    print(filepath)

if __name__ == '__main__':
    main()
