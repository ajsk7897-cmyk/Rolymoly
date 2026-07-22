import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Tuple, Optional

from config import TIER_SCORE_MAP, TIER_ORDER

# 로깅 설정
logger = logging.getLogger(__name__)

def calculate_power_score(solo_tier_str: str, flex_tier_str: str) -> int:
    """
    솔로랭크와 자유랭크 티어를 기반으로 파워스코어 계산
    """
    def get_solo_points(tier_str: str) -> int:
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
            return 600  # Fallback for Master if no LP
            
        for k, v in TIER_SCORE_MAP.items():
            if clean_tier.startswith(k):
                return v
        return 0

    def get_flex_points(tier_str: str) -> int:
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


def calculate_clan_tier(base_score: int, final_score: Optional[int] = None) -> str:
    """
    파워스코어 기반 클랜 티어 계산
    """
    if final_score is None:
        final_score = base_score
        
    sorted_tiers = sorted(TIER_SCORE_MAP.items(), key=lambda x: x[1], reverse=True)
    
    # Strict mapping based on final_score
    for tier, score in sorted_tiers:
        if final_score >= score:
            return tier
    return "Iron 4"

def fetch_tier_data(riot_id: str, tag_line: str) -> Tuple[str, str, int]:
    """
    OP.GG에서 티어 정보 크롤링
    실패시 Unranked 반환
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
        logger.error(f"Error fetching data for {riot_id}#{tag_line}: {e}")
        
    power_score = calculate_power_score(solo_tier, flex_tier)
    
    return solo_tier, flex_tier, power_score

def abbreviate_tier(tier_str: str) -> str:
    """
    티어 문자열을 약어로 변환
    예: "Platinum 4" -> "P4", "Challenger" -> "CH"
    """
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
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import TIER_SCORE_MAP, TIER_ORDER
    print(fetch_tier_data("Hide on bush", "KR1"))
