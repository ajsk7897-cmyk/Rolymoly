import requests
import urllib.parse
import re

url = f"https://www.op.gg/summoners/kr/{urllib.parse.quote('용트름장인')}-{urllib.parse.quote('끄어억')}"
res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
idx1 = res.text.find('platinum 1')
idx2 = res.text.find('diamond 1')

print("Before platinum:", res.text[idx1-100:idx1])
print("Before diamond:", res.text[idx2-100:idx2])
