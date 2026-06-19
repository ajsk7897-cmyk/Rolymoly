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
    "Master": 600, "Grandmaster": 800, "Challenger": 1000
}

def calculate_power_score(solo_tier_str, flex_tier_str):
    def get_base_points(tier_str):
        if not tier_str or tier_str == "Unranked":
            return 0
        # Clean tier string, e.g., "Diamond 1", "Master"
        clean_tier = re.sub(r' \d+ LP', '', tier_str).strip()
        
        matched_score = 0
        for k, v in TIER_SCORE_MAP.items():
            if clean_tier.startswith(k):
                matched_score = v
                break
                
        return matched_score

    solo_points = get_base_points(solo_tier_str)
    flex_points = int(get_base_points(flex_tier_str) * 0.1) # 10% of base score, truncated
    return solo_points + flex_points

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
                        m = re.match(r'([A-Za-z]+)\s*(\d)?', tier_part)
                        if m:
                            t_str = m.group(1).title()
                            d_str = m.group(2) if m.group(2) else ""
                            # Special case: Master/Grandmaster/Challenger usually don't need division in our map
                            if t_str in ["Master", "Grandmaster", "Challenger"]:
                                solo_tier = t_str
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
                    solo_tier = t_solo
                elif solo_tier == "Unranked":
                    solo_tier = t_solo

    except Exception as e:
        print(f"Error fetching data for {riot_id}#{tag_line}: {e}")
        pass
        
    power_score = calculate_power_score(solo_tier, flex_tier)
    
    return solo_tier, flex_tier, power_score

# For testing
if __name__ == "__main__":
    print(fetch_tier_data("Hide on bush", "KR1"))
