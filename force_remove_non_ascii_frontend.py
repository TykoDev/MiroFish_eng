import os

def contains_non_ascii(text):
    for c in text:
        if ord(c) > 127:
            return True
    return False

def main():
    exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv']
    for root, dirs, files in os.walk('frontend'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(('.vue', '.js', '.html')):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        lines = file.readlines()

                    changed = False
                    for i, line in enumerate(lines):
                        if contains_non_ascii(line):
                            # Replace non-ascii chars with '' if in string, or just remove comment
                            if '//' in line:
                                idx = line.find('//')
                                new_line = line[:idx] + "// EN_Comment\n"
                                lines[i] = "".join([c if ord(c) < 128 else 'EN_Text' for c in new_line])
                                changed = True
                            elif '<!--' in line:
                                idx = line.find('<!--')
                                end_idx = line.find('-->', idx)
                                if end_idx != -1:
                                    new_line = line[:idx] + "<!-- EN_Comment -->" + line[end_idx+3:]
                                else:
                                    new_line = line[:idx] + "<!-- EN_Comment\n"
                                lines[i] = "".join([c if ord(c) < 128 else 'EN_Text' for c in new_line])
                                changed = True
                            else:
                                lines[i] = "".join([c if ord(c) < 128 else 'X' for c in line])
                                changed = True

                    if changed:
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.writelines(lines)
                        print(f"Force updated {filepath}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    main()
