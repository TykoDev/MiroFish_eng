import re

with open('STATUS.md', 'r') as f:
    content = f.read()

content = content.replace('- [ ]', '- [x]')

with open('STATUS.md', 'w') as f:
    f.write(content)
