import requests
import re

res = requests.get('https://www.op.gg/summoners/kr/Hide%20on%20bush-KR1', headers={'User-Agent': 'Mozilla/5.0'})
print("Search RANKED:")
for m in re.finditer(r'.{0,40}RANKED.{0,40}', res.text, re.I):
    print(m.group())
    
print("\nSearch tier_info:")
for m in re.finditer(r'.{0,60}tier_info.{0,60}', res.text, re.I):
    print(m.group())
