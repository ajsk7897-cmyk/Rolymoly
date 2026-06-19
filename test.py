import requests
import urllib.parse
import re

url = f"https://www.op.gg/summoners/kr/{urllib.parse.quote('용트름장인')}-{urllib.parse.quote('끄어억')}"
res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
m = re.search(r'<meta name="description" content="([^"]+)">', res.text)
print(m.group(1) if m else "No Meta")
