import requests
import urllib.parse
import re

def test_caption(riot_id, tag_line):
    url = f"https://www.op.gg/summoners/kr/{urllib.parse.quote(riot_id)}-{urllib.parse.quote(tag_line)}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    # Try caption method
    solo = re.search(r'caption>Ranked Solo/Duo</caption>.*?first-letter:uppercase">([^<]+)</strong>', res.text)
    flex = re.search(r'caption>Ranked Flex</caption>.*?first-letter:uppercase">([^<]+)</strong>', res.text)
    
    print(f"[{riot_id}] Caption Solo:", solo.group(1) if solo else "Not Found")
    print(f"[{riot_id}] Caption Flex:", flex.group(1) if flex else "Not Found")
    
test_caption("Hide on bush", "KR1")
test_caption("용트름장인", "끄어억")
test_caption("Paka", "KR1")
