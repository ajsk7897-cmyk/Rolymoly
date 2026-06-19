import requests
import urllib.parse
import re

def test_poro(riot_id, tag_line):
    # Poro.gg uses /summoner/kr/닉네임-태그
    url = f"https://poro.gg/summoner/kr/{urllib.parse.quote(riot_id)}-{urllib.parse.quote(tag_line)}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Poro.gg [{riot_id}]: {res.status_code}")
    
    # Try finding tier
    m = re.search(r'자유랭크.*?<div class="tier">([^<]+)</div>', res.text, re.DOTALL | re.IGNORECASE)
    if m:
        print("Poro Flex Match:", m.group(1))
    else:
        # Poro.gg might have different HTML
        m2 = re.search(r'자유랭크.*?([A-Z]+ \d+)', res.text, re.DOTALL | re.IGNORECASE)
        if m2:
            print("Poro Flex Match 2:", m2.group(1))
        else:
            print("Poro Flex NOT FOUND")

def test_dakgg(riot_id, tag_line):
    # dak.gg uses /lol/profile/kr/닉네임-태그
    url = f"https://dak.gg/lol/profile/kr/{urllib.parse.quote(riot_id)}-{urllib.parse.quote(tag_line)}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Dak.gg [{riot_id}]: {res.status_code}")
    
    # dak.gg usually uses text like "Ranked Flex" or "자유 랭크"
    # let's look for any tier string near "자유"
    m = re.search(r'자유 랭크.*?([A-Za-z]+ \d+)', res.text, re.DOTALL | re.IGNORECASE)
    if m:
        print("Dak Flex Match:", m.group(1))
    else:
        # maybe "Ranked Flex"
        m2 = re.search(r'Ranked Flex.*?([A-Za-z]+ \d+)', res.text, re.DOTALL | re.IGNORECASE)
        if m2:
            print("Dak Flex Match 2:", m2.group(1))
        else:
            print("Dak Flex NOT FOUND")

test_poro("용트름장인", "끄어억")
test_dakgg("용트름장인", "끄어억")
