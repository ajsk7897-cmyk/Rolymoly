import os
import re

files_bg = {
    '1_가입.py': 'Portfolio_img_10220755_1.gif',
    '3_회원리스트.py': 'images (1).jpg',
    '4_일반내전.py': 'images (2).jpg',
    '5_경매내전.py': 'images (3).jpg',
    '6_내전이력.py': 'images.jpg',
    '7_회원관리(운영진용).py': '190aa82672754bd77.gif'
}

for filename, bg in files_bg.items():
    p = os.path.join('pages', filename)
    with open(p, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # We will replace the entire line containing set_background
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'set_background' in line and 'import' not in line:
            lines[i] = f'set_background("{bg}")'
    
    with open(p, 'w', encoding='utf-8') as file:
        file.write('\n'.join(lines))

# app.py
p = 'app.py'
with open(p, 'r', encoding='utf-8') as file:
    content = file.read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'set_background' in line and 'import' not in line:
        lines[i] = 'set_background("190aa82672754bd77.gif")'
with open(p, 'w', encoding='utf-8') as file:
    file.write('\n'.join(lines))
    
print("Fixed syntax for real")
