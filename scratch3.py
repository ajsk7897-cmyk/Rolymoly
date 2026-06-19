import requests
import urllib.parse
import re

def get_fow_flex(riot_id, tag_line):
    url = f"https://fow.kr/find/{urllib.parse.quote(riot_id)}-{tag_line}"
    try:
        res = requests.get(url, timeout=5)
        # fow.kr text has things like "자유 5:5 랭크" and "PLATINUM 4"
        # We can extract all tier texts
        tiers = re.findall(r'([A-Z]+ \d+)\s*-', res.text)
        print("Tiers found:", tiers)
        
        # let's look around '자유'
        idx = res.text.find('자유')
        if idx != -1:
            snippet = res.text[idx:idx+200]
            print("Snippet around 자유:", snippet)
            m = re.search(r'([A-Z]+ [IV]+)', snippet)
            if m:
                print("Flex:", m.group(1))
    except Exception as e:
        print(e)
        
get_fow_flex("Hide on bush", "KR1")
get_fow_flex("Paka", "KR1")
