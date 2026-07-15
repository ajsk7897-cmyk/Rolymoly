import requests
from bs4 import BeautifulSoup
import re

TIER_SCORE_MAP = {
    "Iron 4": 10, "Iron 3": 10, "Iron 2": 10, "Iron 1": 10,
    "Bronze 4": 20, "Bronze 3": 30, "Bronze 2": 40, "Bronze 1": 50,
    "Silver 4": 60, "Silver 3": 70, "Silver 2": 80, "Silver 1": 90,
    "Gold 4": 120, "Gold 3": 130, "Gold 2": 140, "Gold 1": 150,
    "Platinum 4": 200, "Platinum 3": 210, "Platinum 2": 220, "Platinum 1": 230,
    "Emerald 4": 280, "Emerald 3": 300, "Emerald 2": 320, "Emerald 1": 340,
    "Diamond 4": 390, "Diamond 3": 420, "Diamond 2": 450, "Diamond 1": 480,
    "Master": 550, "Grandmaster": 800, "Challenger": 1000
}

TIER_ORDER = [
    "Iron 4", "Iron 3", "Iron 2", "Iron 1",
    "Bronze 4", "Bronze 3", "Bronze 2", "Bronze 1",
    "Silver 4", "Silver 3", "Silver 2", "Silver 1",
    "Gold 4", "Gold 3", "Gold 2", "Gold 1",
    "Platinum 4", "Platinum 3", "Platinum 2", "Platinum 1",
    "Emerald 4", "Emerald 3", "Emerald 2", "Emerald 1",
    "Diamond 4", "Diamond 3", "Diamond 2", "Diamond 1",
    "Master", "Grandmaster", "Challenger"
]

def calculate_power_score(solo_tier_str, flex_tier_str):
    def get_solo_points(tier_str):
        if not tier_str or tier_str == "Unranked":
            return 0
            
        clean_tier = re.sub(r' \d+ LP', '', tier_str).strip()
        
        # Check Master LP
        if clean_tier == "Master":
            lp_match = re.search(r'(\d+) LP', tier_str)
            if lp_match:
                lp = int(lp_match.group(1))
                if lp >= 200:
                    return 700
                elif lp >= 100:
                    return 600
                else:
                    return 550
            return 600 # Fallback for Master if no LP
            
        for k, v in TIER_SCORE_MAP.items():
            if clean_tier.startswith(k):
                return v
        return 0

    def get_flex_points(tier_str):
        if not tier_str or tier_str == "Unranked":
            return 0
        clean_tier = re.sub(r' \d+ LP', '', tier_str).strip()
        
        if clean_tier in TIER_ORDER:
            return TIER_ORDER.index(clean_tier) + 1
            
        for t in TIER_ORDER:
            if clean_tier.startswith(t):
                return TIER_ORDER.index(t) + 1
        return 0

    solo_points = get_solo_points(solo_tier_str)
    flex_points = get_flex_points(flex_tier_str)
    return solo_points + flex_points

def calculate_mmr_delta(solo_tier_str, is_win=True):
    if not solo_tier_str or solo_tier_str == "Unranked":
        return 2 # default for unranked
        
    clean_tier = re.sub(r' \d+ LP', '', solo_tier_str).strip()
    
    # Check if exact match exists in TIER_ORDER
    matched_tier = None
    for t in TIER_ORDER:
        if clean_tier.startswith(t):
            matched_tier = t
            break
            
    if not matched_tier:
        return 2
        
    idx = TIER_ORDER.index(matched_tier)
    curr_score = TIER_SCORE_MAP.get(matched_tier, 0)
    
    if is_win:
        if matched_tier == "Challenger":
            return 10
        next_tier = TIER_ORDER[idx + 1]
        next_score = TIER_SCORE_MAP.get(next_tier, 0)
        diff = next_score - curr_score
    else:
        if matched_tier == "Iron 4":
            return 2
        prev_tier = TIER_ORDER[idx - 1]
        prev_score = TIER_SCORE_MAP.get(prev_tier, 0)
        diff = curr_score - prev_score
    
    if diff < 0:
        diff = 10
        
    delta = diff // 5
    return max(1, delta)

def calculate_clan_tier(base_score, final_score=None):
    if final_score is None:
        final_score = base_score
        
    sorted_tiers = sorted(TIER_SCORE_MAP.items(), key=lambda x: x[1], reverse=True)
    
    # Strict mapping based on final_score
    for tier, score in sorted_tiers:
        if final_score >= score:
            return tier
    return "Iron 4"

def fetch_tier_data(riot_id, tag_line):
    """
    Crawls OP.GG to fetch tier information.
    Currently uses simple scraping. If blocked, returns Unranked safely.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    url = f"https://www.op.gg/summoners/kr/{riot_id}-{tag_line}"
    
    solo_tier = "Unranked"
    flex_tier = "Unranked"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Method 1: Parse the meta description (Reliable for Solo Rank)
            meta = soup.find('meta', {'name': 'description'})
            if meta and 'content' in meta.attrs:
                content = meta['content']
                parts = [p.strip() for p in content.split(' / ')]
                if len(parts) > 1:
                    tier_part = parts[1]
                    # Format: "Platinum 4 12LP" or "Challenger 1 1684LP"
                    if 'Win' not in tier_part and 'Lose' not in tier_part:
                        m = re.match(r'([A-Za-z]+)\s*(\d)?\s*(\d+)?LP?', tier_part.replace(' ', ''))
                        if not m:
                            # Try simple split
                            m = re.match(r'([A-Za-z]+)\s*(\d)?', tier_part)
                            
                        if m:
                            t_str = m.group(1).title()
                            d_str = m.group(2) if m.group(2) else ""
                            # Special case: Master/Grandmaster/Challenger
                            if t_str in ["Master", "Grandmaster", "Challenger"]:
                                lp_str = ""
                                lp_match = re.search(r'(\d+)LP', tier_part.replace(' ', ''))
                                if lp_match:
                                    lp_str = f" {lp_match.group(1)} LP"
                                solo_tier = f"{t_str}{lp_str}"
                            else:
                                solo_tier = f"{t_str} {d_str}".strip()
            
            # Method 2: Parse all displayed tiers in the HTML
            # OP.GG typically renders each tier twice (Desktop & Mobile views).
            # If a user has both Solo and Flex ranks, there will be 4 tier strings.
            # Example: ['platinum 1', 'platinum 1', 'diamond 1', 'diamond 1']
            # If a user has only one rank, there will be 2 tier strings.
            tiers = re.findall(r'first-letter:uppercase">([^<]+)</strong>', response.text)
            
            if len(tiers) >= 4:
                # Both Solo and Flex exist
                t_solo = tiers[0].title()
                t_flex = tiers[2].title()
                
                if t_solo in ["Master", "Grandmaster", "Challenger"]:
                    solo_tier = t_solo
                elif solo_tier == "Unranked": # Only overwrite if Method 1 didn't find it
                    solo_tier = t_solo
                    
                if t_flex in ["Master", "Grandmaster", "Challenger"]:
                    flex_tier = t_flex
                else:
                    flex_tier = t_flex
                    
            elif len(tiers) >= 2:
                # Only one rank exists (typically Solo Rank)
                t_solo = tiers[0].title()
                if t_solo in ["Master", "Grandmaster", "Challenger"]:
                    if solo_tier == "Unranked": # Only set if Method 1 failed to get LP
                        solo_tier = t_solo
                elif solo_tier == "Unranked":
                    solo_tier = t_solo

    except Exception as e:
        print(f"Error fetching data for {riot_id}#{tag_line}: {e}")
        pass
        
    power_score = calculate_power_score(solo_tier, flex_tier)
    
    return solo_tier, flex_tier, power_score

def abbreviate_tier(tier_str):
    if not tier_str or tier_str == "Unranked":
        return "UR"
    
    mapping = {
        "Iron": "I",
        "Bronze": "B",
        "Silver": "S",
        "Gold": "G",
        "Platinum": "P",
        "Emerald": "E",
        "Diamond": "D",
        "Master": "M",
        "Grandmaster": "GM",
        "Challenger": "CH"
    }
    
    for full, short in mapping.items():
        if tier_str.startswith(full):
            rest = tier_str[len(full):].strip()
            if rest:
                if "LP" in rest:
                    return f"{short} {rest}"
                else:
                    return f"{short}{rest}"
            return short
    return tier_str

# For testing
if __name__ == "__main__":
    print(fetch_tier_data("Hide on bush", "KR1"))
