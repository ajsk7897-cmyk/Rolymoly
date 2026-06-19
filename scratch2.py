import requests
from bs4 import BeautifulSoup

res = requests.get('https://dak.gg/lol/profile/Hide%20on%20bush-KR1', headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(res.text, 'html.parser')

print("Status:", res.status_code)
# Search for solo rank and flex rank divs
for div in soup.find_all('div'):
    text = div.get_text(strip=True)
    if "솔로 랭크" in text or "자유 랭크" in text or "Solo" in text or "Flex" in text:
        # Check parent or siblings
        pass

# simpler approach: just print the text to see if the tier is there
print(soup.text[:1000])

# Wait, we can just extract from OP.GG using a very robust regex:
# OP.GG returns this string: "queue_translate":"RANKED_FLEX_SR" ... "tier_info":{"tier":"GOLD","division":2}
import re
opgg_res = requests.get('https://www.op.gg/summoners/kr/Hide%20on%20bush-KR1', headers={'User-Agent': 'Mozilla/5.0'})
flex = re.search(r'"queue_translate":"[A-Za-z_]+FLEX[A-Za-z_]+".*?"tier_info":\{"tier":"([^"]+)","division":(\d+)', opgg_res.text)
if flex:
    print("OPGG Flex:", flex.group(1), flex.group(2))
else:
    print("OPGG Flex NOT FOUND")
