import os, re
updated = []
for root, _, files in os.walk('pages'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = re.sub(
                r'st\.columns\(([^)]+)\)',
                lambda m: m.group(0) if 'vertical_alignment' in m.group(1) else f'st.columns({m.group(1)}, vertical_alignment="bottom")',
                content
            )
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                updated.append(path)
print('Updated:', updated)
