import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def get_tiers(riot_id, tag_line):
    url = f"https://fow.kr/find/{urllib.parse.quote(riot_id)}-{tag_line}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        # fow.kr uses EUC-KR but we can just regex the text directly.
        # Find all blocks of text
        soup = BeautifulSoup(res.text, 'html.parser')
        
        solo = "Unranked"
        flex = "Unranked"
        
        # In fow.kr, the rank is usually inside a div with class 'profile'
        # Or we can just do raw regex.
        # It says "솔로 5:5 랭크" then some tags then "PLATINUM 4 - 12pt"
        # It says "자유 5:5 랭크" then some tags then "GOLD 2 - 40pt"
        
        solo_match = re.search(r'솔로 5:5 랭크.*?([A-Z]+ [1-4])', res.text, re.DOTALL)
        if solo_match:
            solo = solo_match.group(1).title()
            
        flex_match = re.search(r'자유 5:5 랭크.*?([A-Z]+ [1-4])', res.text, re.DOTALL)
        if flex_match:
            flex = flex_match.group(1).title()
            
        # What about Challenger/Grandmaster/Master which don't have 1-4? Actually they do in FOW! "CHALLENGER 1"
        # Let's adjust regex to match ([A-Z]+ \d+) or ([A-Z]+)
        
        solo_match2 = re.search(r'솔로 5:5 랭크.*?([A-Z]{4,})\s*(\d*)', res.text, re.DOTALL)
        if solo_match2:
            t = solo_match2.group(1).title()
            d = solo_match2.group(2)
            if t in ["Master", "Grandmaster", "Challenger"]:
                solo = t
            elif d:
                solo = f"{t} {d}"
                
        flex_match2 = re.search(r'자유 5:5 랭크.*?([A-Z]{4,})\s*(\d*)', res.text, re.DOTALL)
        if flex_match2:
            t = flex_match2.group(1).title()
            d = flex_match2.group(2)
            if t in ["Master", "Grandmaster", "Challenger"]:
                flex = t
            elif d:
                flex = f"{t} {d}"
                
        print(f"[{riot_id}] Solo: {solo}, Flex: {flex}")
        
    except Exception as e:
        print(e)
        
get_tiers("Hide on bush", "KR1")
get_tiers("Destiny", "KR1")
get_tiers("Paka", "KR1")
