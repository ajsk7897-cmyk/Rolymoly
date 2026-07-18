import os
import re

for f in os.listdir('pages'):
    if not f.endswith('.py'): continue
    p = os.path.join('pages', f)
    with open(p, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Let's just fix any mismatched quotes in set_background
    # It currently looks like: set_background("images (1).jpg') or set_background('images (1).jpg") etc
    # We will just replace the whole line or find set_background(.*) and clean it.
    
    def fix_match(m):
        inner = m.group(1)
        # remove any quotes
        inner = inner.replace('"', '').replace("'", '')
        return f'set_background("{inner}")'
        
    content = re.sub(r'set_background\(([^)]+)\)', fix_match, content)
    
    with open(p, 'w', encoding='utf-8') as file:
        file.write(content)

# Also fix app.py
p = 'app.py'
with open(p, 'r', encoding='utf-8') as file:
    content = file.read()
content = re.sub(r'set_background\(([^)]+)\)', fix_match, content)
with open(p, 'w', encoding='utf-8') as file:
    file.write(content)
    
print("Fixed syntax")
