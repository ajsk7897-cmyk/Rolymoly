"""
공통 유틸리티 함수 모음
"""
from typing import Tuple, Dict, List, Any
from utils.tier_fetcher import calculate_clan_tier, abbreviate_tier


def unpack_user_data(user: Tuple) -> Dict[str, Any]:
    """
    사용자 데이터 튜플을 딕셔너리로 언패킹
    데이터 구조가 12개 또는 10개 필드일 수 있음
    """
    if len(user) == 12:
        user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus, main_pos, sub_pos = user
    else:
        user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus = user
        main_pos, sub_pos = "", ""
    
    return {
        'user_id': user_id,
        'riot_id': riot_id,
        'tag_line': tag_line,
        'solo_tier': solo_tier,
        'flex_tier': flex_tier,
        'power_score': power_score,
        'manual_score': manual_score,
        'manual_stars': manual_stars,
        'is_admin': is_admin,
        'match_bonus': match_bonus,
        'main_pos': main_pos,
        'sub_pos': sub_pos
    }


def calculate_user_scores(user_dict: Dict[str, Any]) -> Tuple[int, int, str]:
    """
    사용자의 점수 계산 (기본 점수, 최종 점수, 클랜 티어)
    """
    base_score = user_dict['manual_score'] if user_dict['manual_score'] != -1 else user_dict['power_score']
    final_score = base_score + user_dict['match_bonus']
    clan_tier = calculate_clan_tier(base_score, final_score)
    return base_score, final_score, clan_tier


def format_user_display(user: Tuple, show_score: bool = True) -> str:
    """
    사용자 표시용 문자열 생성
    예: "[D1] Hide on bush#KR1 (스코어: 1100)"
    """
    user_dict = unpack_user_data(user)
    _, final_score, clan_tier = calculate_user_scores(user_dict)
    abbr_tier = abbreviate_tier(clan_tier)
    
    if show_score:
        return f"[{abbr_tier}] {user_dict['riot_id']}#{user_dict['tag_line']} (스코어: {final_score})"
    else:
        return f"[{abbr_tier}] {user_dict['riot_id']}#{user_dict['tag_line']}"


def format_user_for_selectbox(user: Tuple) -> Tuple[str, int, int, str, str, str]:
    """
    selectbox용 사용자 데이터 포맷
    Returns: (표시문자열, user_id, final_score, abbr_tier, main_pos, sub_pos)
    """
    user_dict = unpack_user_data(user)
    _, final_score, clan_tier = calculate_user_scores(user_dict)
    abbr_tier = abbreviate_tier(clan_tier)
    
    display_str = format_user_display(user, show_score=True)
    return (display_str, user_dict['user_id'], final_score, abbr_tier, 
            user_dict['main_pos'], user_dict['sub_pos'], user_dict['manual_stars'])


def calculate_auction_points(tier_score: int) -> int:
    """
    티어 점수에 따른 경매 시작 포인트 계산
    """
    from config import AUCTION_POINTS_TABLE, AUCTION_DEFAULT_POINTS_VALUE
    
    for threshold, points in AUCTION_POINTS_TABLE:
        if tier_score >= threshold:
            return points
    return AUCTION_DEFAULT_POINTS_VALUE


def calculate_trophy_symbols(total_points: int) -> str:
    """
    총 포인트를 트로피/메달/별 이모지로 변환
    """
    trophies = total_points // 25
    medals = (total_points % 25) // 5
    stars = total_points % 5
    
    symbol_str = ""
    if trophies > 0:
        symbol_str += "🏆" * trophies
    if medals > 0:
        symbol_str += "🎖️" * medals
    if stars > 0:
        symbol_str += "⭐" * stars
    if not symbol_str:
        symbol_str = "-"
    
    return symbol_str


def validate_riot_id(riot_id_full: str) -> Tuple[bool, str, str]:
    """
    롤 아이디 형식 검증
    Returns: (성공여부, riot_id, tag_line)
    """
    if "#" not in riot_id_full:
        return False, "", ""
    
    riot_id, tag_line = riot_id_full.split("#", 1)
    riot_id = riot_id.strip()
    tag_line = tag_line.strip()
    
    if not riot_id or not tag_line:
        return False, "", ""
    
    return True, riot_id, tag_line


def validate_positions(main_pos: str, sub_pos: str) -> bool:
    """
    포지션 중복 검증
    """
    return main_pos != sub_pos


def get_match_bonus_change(base_score: int, is_win: bool) -> int:
    """
    내전 결과에 따른 MMR 증감량 계산
    """
    from utils.tier_fetcher import calculate_mmr_delta, calculate_clan_tier
    
    effective_tier = calculate_clan_tier(base_score)
    return calculate_mmr_delta(effective_tier, is_win=is_win)


def format_score_change(bonus_change: int, is_win: bool) -> str:
    """
    점수 증감 문자열 포맷
    """
    if is_win:
        return f"+{bonus_change}점"
    else:
        return f"-{bonus_change}점"


def safe_int(value: Any, default: int = 0) -> int:
    """
    안전한 정수 변환
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_get_nested(data: Dict, keys: List[str], default: Any = None) -> Any:
    """
    중첩 딕셔너리 안전하게 접근
    """
    result = data
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default
    return result