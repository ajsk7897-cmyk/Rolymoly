import requests
import urllib.parse
import re

url = f"https://www.op.gg/summoners/kr/{urllib.parse.quote('용트름장인')}-{urllib.parse.quote('끄어억')}"
res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
tiers = re.findall(r'first-letter:uppercase">([^<]+)</strong>', res.text)
print("All tiers found:", tiers)
