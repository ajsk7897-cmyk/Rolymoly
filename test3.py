import requests
import urllib.parse
import re

def test_user(riot_id, tag_line):
    url = f"https://www.op.gg/summoners/kr/{urllib.parse.quote(riot_id)}-{urllib.parse.quote(tag_line)}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    tiers = re.findall(r'first-letter:uppercase">([^<]+)</strong>', res.text)
    
    # Let's also find surrounding context, like "Ranked Solo" or "Ranked Flex"
    # Actually, OP.GG HTML might say "Ranked Solo" before the first one
    solo = re.search(r'Ranked Solo/Duo.*?first-letter:uppercase">([^<]+)</strong>', res.text)
    flex = re.search(r'Ranked Flex.*?first-letter:uppercase">([^<]+)</strong>', res.text)
    
    print(f"[{riot_id}] All: {tiers}")
    print(f"[{riot_id}] Solo Search:", solo.group(1) if solo else "Not Found")
    print(f"[{riot_id}] Flex Search:", flex.group(1) if flex else "Not Found")

test_user("Hide on bush", "KR1")
test_user("용트름장인", "끄어억")
test_user("Paka", "KR1")
