import re
with open('backend/requirements.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if re.search(r'[\u4e00-\u9fff]', line):
            print(repr(line.strip()))
