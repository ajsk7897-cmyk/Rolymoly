import os
import re

for f in os.listdir('pages'):
    if not f.endswith('.py'): continue
    p = os.path.join('pages', f)
    with open(p, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace single quotes to double quotes inside set_background()
    content = re.sub(r'set_background\([^)]+\)', lambda m: m.group(0).replace("'", '"'), content)
    
    with open(p, 'w', encoding='utf-8') as file:
        file.write(content)
print("Fixed")
