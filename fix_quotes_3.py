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
    
    # regex to find set_background(...) no matter what's inside
    # Because of parentheses inside the string, we'll use a lazy match up to the end of the line
    content = re.sub(r'set_background\(.*?\)', f'set_background("{bg}")', content)
    
    with open(p, 'w', encoding='utf-8') as file:
        file.write(content)

# app.py
p = 'app.py'
with open(p, 'r', encoding='utf-8') as file:
    content = file.read()
content = re.sub(r'set_background\(.*?\)', 'set_background("190aa82672754bd77.gif")', content)
with open(p, 'w', encoding='utf-8') as file:
    file.write(content)
    
print("Fixed syntax safely")
