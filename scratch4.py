import requests
from bs4 import BeautifulSoup

res = requests.get('https://poro.gg/summoner/kr/Hide%20on%20bush-KR1', headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(res.text, 'html.parser')

print("Status:", res.status_code)
# Search for solo rank and flex rank divs
for div in soup.find_all('div', class_='tier-string'):
    print(div.get_text(strip=True))

for div in soup.find_all('div'):
    if "자유" in div.get_text():
        # find the tier
        pass
        
# let's just use re
import re
print("Regex:")
for m in re.finditer(r'자유랭크.*?([A-Z]+ \d+)', res.text, re.DOTALL | re.IGNORECASE):
    print(m.group(1))
    
# Or look for 'Ranked Flex' in poro.gg
