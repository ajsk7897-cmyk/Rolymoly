import gspread
import streamlit as st
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional

from config import SPREADSHEET_ID, CACHE_TTL

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_resource
def get_gspread_client():
    """Google Sheets 클라이언트 반환"""
    import json
    try:
        if "gcp_service_account" in st.secrets:
            # Streamlit Cloud Secrets 사용
            secret_val = st.secrets["gcp_service_account"]
            if isinstance(secret_val, str):
                creds_dict = json.loads(secret_val)
            else:
                creds_dict = dict(secret_val)
            logger.info("Streamlit Cloud Secrets로 인증")
            return gspread.service_account_from_dict(creds_dict)
    except Exception as e:
        logger.warning(f"Secrets 로드 실패, 로컬 파일 시도: {e}")
        
    # 로컬 환경 (credentials.json 파일 사용)
    try:
        return gspread.service_account(filename="credentials.json")
    except Exception as e:
        logger.error(f"credentials.json 로드 실패: {e}")
        raise

@st.cache_resource
def get_sheet():
    gc = get_gspread_client()
    return gc.open_by_key(SPREADSHEET_ID)

@st.cache_resource
def get_worksheet(sheet_name):
    sh = get_sheet()
    return sh.worksheet(sheet_name)

# init_db is not needed actively if we already created sheets via script, 
# but we keep it empty or simple to avoid errors from other files
def init_db():
    pass

def clear_cache():
    st.cache_data.clear()

@st.cache_data(ttl=CACHE_TTL)
def get_all_settings() -> List[Dict[str, str]]:
    """설정 시트에서 모든 설정 반환"""
    try:
        settings_sheet = get_worksheet("settings")
        records = settings_sheet.get_all_records()
        return records
    except Exception as e:
        logger.error(f"설정 로드 실패: {e}")
        return []

def get_admin_password() -> str:
    """관리자 비밀번호 반환"""
    records = get_all_settings()
    for row in records:
        if row.get('key') == 'admin_password':
            return row.get('value', 'admin1234')
    return 'admin1234'

def set_admin_password(new_password: str) -> bool:
    """관리자 비밀번호 설정"""
    try:
        settings_sheet = get_worksheet("settings")
        cell = settings_sheet.find("admin_password", in_column=1)
        if cell:
            settings_sheet.update_cell(cell.row, cell.col + 1, new_password)
            clear_cache()
            logger.info("관리자 비밀번호 변경 완료")
            return True
        return False
    except Exception as e:
        logger.error(f"비밀번호 설정 실패: {e}")
        return False

def _get_next_id(sheet) -> int:
    """시트에서 다음 ID 생성"""
    try:
        records = sheet.get_all_records()
        if not records:
            return 1
        ids = [int(r['id']) for r in records if str(r.get('id', '')).isdigit()]
        return max(ids) + 1 if ids else 1
    except Exception as e:
        logger.error(f"ID 생성 실패: {e}")
        return 1

def add_user(riot_id: str, tag_line: str, birthdate: str, main_position: str = '', sub_position: str = '') -> bool:
    """새 사용자 추가"""
    try:
        users_sheet = get_worksheet("users")
        next_id = _get_next_id(users_sheet)
        users_sheet.append_row([
            next_id, riot_id, f"'{tag_line}", f"'{birthdate}", "PENDING", "Unranked", "Unranked", 0, -1, 0, 0, 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, main_position, sub_position
        ], value_input_option='USER_ENTERED')
        clear_cache()
        logger.info(f"사용자 추가 완료: {riot_id}#{tag_line}")
        return True
    except Exception as e:
        logger.error(f"사용자 추가 실패: {e}")
        return False

@st.cache_data(ttl=CACHE_TTL)
def get_all_users() -> List[Dict[str, str]]:
    """모든 사용자 조회"""
    try:
        users_sheet = get_worksheet("users")
        rows = users_sheet.get_all_values()
        if not rows or len(rows) < 2:
            return []
        headers = rows[0]
        records = []
        for row in rows[1:]:
            padded_row = row + [''] * (len(headers) - len(row))
            record = {h: (val[1:] if isinstance(val, str) and val.startswith("'") else val) 
                      for h, val in zip(headers, padded_row)}
            records.append(record)
        return records
    except Exception as e:
        logger.error(f"사용자 조회 실패: {e}")
        return []

def get_pending_users() -> List[tuple]:
    """승인 대기 중인 사용자 목록"""
    users = get_all_users()
    pending = []
    for u in users:
        if u.get('status') == 'PENDING':
            pending.append((u['id'], u['riot_id'], u['tag_line'], u['birthdate']))
    return pending

def get_all_approved_users() -> List[tuple]:
    """승인된 사용자 목록"""
    users = get_all_users()
    approved = []
    for u in users:
        if u.get('status') == 'APPROVED':
            approved.append((
                int(u['id']), u['riot_id'], u['tag_line'], u['solo_tier'], 
                u['flex_tier'], int(u['power_score']), int(u['manual_score']), 
                int(u['manual_stars']), int(u['is_admin']), 
                int(u.get('match_bonus', 0) if str(u.get('match_bonus', '')) != '' else 0),
                u.get('main_position', ''), u.get('sub_position', '')
            ))
    return approved

def approve_user(user_id: int, solo_tier: str, flex_tier: str, power_score: int) -> bool:
    """사용자 승인"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update(f"E{cell.row}:H{cell.row}", [["APPROVED", solo_tier, flex_tier, power_score]])
            clear_cache()
            logger.info(f"사용자 승인 완료: ID {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"사용자 승인 실패: {e}")
        return False

def update_user_tier_info(user_id: int, solo_tier: str, flex_tier: str, power_score: int) -> bool:
    """사용자 티어 정보 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update(f"F{cell.row}:H{cell.row}", [[solo_tier, flex_tier, power_score]])
            clear_cache()
            logger.info(f"티어 정보 업데이트 완료: ID {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"티어 정보 업데이트 실패: {e}")
        return False

def batch_update_user_tiers(tier_updates: Dict[int, tuple]) -> bool:
    """여러 사용자의 티어 정보 일괄 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        users = get_all_users()
        
        updates = []
        for idx, u in enumerate(users):
            uid = int(u['id'])
            if uid in tier_updates:
                solo_tier, flex_tier, power_score = tier_updates[uid]
                cell_row = idx + 2
                updates.append({'range': f"F{cell_row}:H{cell_row}", 'values': [[solo_tier, flex_tier, power_score]]})
                
        if updates:
            users_sheet.batch_update(updates)
            clear_cache()
            logger.info(f"일괄 티어 업데이트 완료: {len(updates)}명")
            return True
        return False
    except Exception as e:
        logger.error(f"일괄 티어 업데이트 실패: {e}")
        return False

def reject_user(user_id: int) -> bool:
    """사용자 가입 거절 (삭제)"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.delete_rows(cell.row)
            clear_cache()
            logger.info(f"사용자 거절/삭제 완료: ID {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"사용자 거절 실패: {e}")
        return False

def update_manual_score(user_id: int, manual_score: int) -> bool:
    """수동 점수 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update_cell(cell.row, 9, manual_score)
            clear_cache()
            logger.info(f"수동 점수 업데이트 완료: ID {user_id} -> {manual_score}")
            return True
        return False
    except Exception as e:
        logger.error(f"수동 점수 업데이트 실패: {e}")
        return False

def update_user_positions(user_id: int, main_pos: str, sub_pos: str) -> bool:
    """사용자 포지션 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        rows = users_sheet.get_all_values()
        headers = rows[0]
        
        col_main = headers.index('main_position') + 1 if 'main_position' in headers else 14
        col_sub = headers.index('sub_position') + 1 if 'sub_position' in headers else 15
        
        if 'main_position' not in headers:
            users_sheet.update_cell(1, 14, 'main_position')
            col_main = 14
        if 'sub_position' not in headers:
            users_sheet.update_cell(1, 15, 'sub_position')
            col_sub = 15

        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update_cell(cell.row, col_main, main_pos)
            users_sheet.update_cell(cell.row, col_sub, sub_pos)
            clear_cache()
            logger.info(f"포지션 업데이트 완료: ID {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"포지션 업데이트 실패: {e}")
        return False

def update_manual_stars(user_id: int, stars: int) -> bool:
    """수동 별 포인트 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update_cell(cell.row, 10, stars)
            clear_cache()
            logger.info(f"수동 별 포인트 업데이트 완료: ID {user_id} -> {stars}")
            return True
        return False
    except Exception as e:
        logger.error(f"수동 별 포인트 업데이트 실패: {e}")
        return False

def update_admin_role(user_id: int, is_admin: int) -> bool:
    """관리자 권한 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update_cell(cell.row, 11, is_admin)
            clear_cache()
            logger.info(f"관리자 권한 업데이트 완료: ID {user_id} -> {is_admin}")
            return True
        return False
    except Exception as e:
        logger.error(f"관리자 권한 업데이트 실패: {e}")
        return False

def kick_user(user_id: int) -> bool:
    """사용자 강퇴"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update_cell(cell.row, 5, 'KICKED')
            clear_cache()
            logger.info(f"사용자 강퇴 완료: ID {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"사용자 강퇴 실패: {e}")
        return False

def delete_all_history() -> bool:
    """모든 내전 이력 삭제"""
    try:
        mp_sheet = get_worksheet("match_players")
        matches_sheet = get_worksheet("matches")
        users_sheet = get_worksheet("users")
        
        # Keep header
        if mp_sheet.row_count > 1:
            mp_sheet.delete_rows(2, mp_sheet.row_count)
            
        if matches_sheet.row_count > 1:
            matches_sheet.delete_rows(2, matches_sheet.row_count)
        
        # Reset match_bonus for all users
        users = get_all_users()
        updates = []
        for idx, u in enumerate(users):
            if str(u.get('match_bonus', '0')) != '0':
                updates.append({'range': f"M{idx+2}", 'values': [[0]]})
        if updates:
            users_sheet.batch_update(updates)
            
        clear_cache()
        logger.info("모든 내전 이력 삭제 완료")
        return True
    except Exception as e:
        logger.error(f"내전 이력 삭제 실패: {e}")
        return False

def delete_match(match_id: int) -> bool:
    """특정 내전 삭제"""
    try:
        matches_sheet = get_worksheet("matches")
        mp_sheet = get_worksheet("match_players")
        users_sheet = get_worksheet("users")
        
        matches = _get_all_matches_raw()
        match_to_delete = next((m for m in matches if str(m['id']) == str(match_id)), None)
        mps = _get_all_match_players_raw()
        
        if match_to_delete and match_to_delete.get('match_type') == 'NORMAL' and match_to_delete.get('winning_team') not in ['아직 모름', '']:
            winning_team = match_to_delete['winning_team']
            users = get_all_users()
            user_dict = {str(u['id']): u for u in users}
            
            updates = []
            for mp in mps:
                if str(mp['match_id']) == str(match_id):
                    uid = str(mp['user_id'])
                    if uid in user_dict:
                        u = user_dict[uid]
                        from utils.tier_fetcher import calculate_mmr_delta, calculate_clan_tier

                        base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
                        effective_tier = calculate_clan_tier(base_score)
                        current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus', '')) != '' else 0)
                        
                        if mp['team_name'] == winning_team:
                            bonus_change = calculate_mmr_delta(effective_tier, is_win=True)
                            current_bonus -= bonus_change # rollback win
                        else:
                            bonus_change = calculate_mmr_delta(effective_tier, is_win=False)
                            current_bonus += bonus_change # rollback loss
                            
                        # Cap at -base_score to prevent final score < 0
                        current_bonus = max(-base_score, current_bonus)
                            
                        cell_row = [idx + 2 for idx, val in enumerate(users) if str(val['id']) == uid][0]
                        updates.append({'range': f"M{cell_row}", 'values': [[current_bonus]]})
            if updates:
                users_sheet.batch_update(updates)

        # Delete match_players rows
        rows_to_delete = []
        for i, mp in enumerate(mps):
            if str(mp['match_id']) == str(match_id):
                rows_to_delete.append(i + 2) 
        
        for r in sorted(rows_to_delete, reverse=True):
            mp_sheet.delete_rows(r)

        # Delete match row
        cell = matches_sheet.find(str(match_id), in_column=1)
        if cell:
            matches_sheet.delete_rows(cell.row)
            
        clear_cache()
        logger.info(f"내전 삭제 완료: Match ID {match_id}")
        return True
    except Exception as e:
        logger.error(f"내전 삭제 실패: {e}")
        return False

@st.cache_data(ttl=CACHE_TTL)
def _get_all_matches_raw() -> List[Dict[str, str]]:
    """모든 매치 데이터 원본 조회"""
    try:
        return get_worksheet("matches").get_all_records()
    except Exception as e:
        logger.error(f"매치 데이터 조회 실패: {e}")
        return []

@st.cache_data(ttl=CACHE_TTL)
def _get_all_match_players_raw() -> List[Dict[str, str]]:
    """모든 매치 플레이어 데이터 원본 조회"""
    try:
        return get_worksheet("match_players").get_all_records()
    except Exception as e:
        logger.error(f"매치 플레이어 데이터 조회 실패: {e}")
        return []

@st.cache_data(ttl=CACHE_TTL)
def get_matches() -> List[tuple]:
    """매치 목록 조회 (날짜순 정렬)"""
    records = _get_all_matches_raw()
    try:
        records = sorted(records, key=lambda x: str(x.get('match_date', '')), reverse=True)
    except Exception:
        pass
    return [(int(r['id']), r['match_type'], r['host'], r['match_date'], r['winning_team']) for r in records]

@st.cache_data(ttl=CACHE_TTL)
def get_match_players(match_id: int) -> List[tuple]:
    """특정 매치의 참가자 목록 조회"""
    mps = [mp for mp in _get_all_match_players_raw() if str(mp.get('match_id')) == str(match_id)]
    users = {str(u['id']): u for u in get_all_users()}
    
    result = []
    for mp in mps:
        uid = str(mp['user_id'])
        if uid in users:
            u = users[uid]
            result.append((
                mp['team_name'], mp['role'], u['riot_id'], u['tag_line'], 
                int(u['power_score']), int(u['manual_score']), int(mp['points_spent']), 
                int(u.get('match_bonus', 0) if str(u.get('match_bonus', '')) != '' else 0)
            ))
    return result

def add_match(match_type: str, host: str, winning_team: str, players_data: List[tuple]) -> bool:
    """새 매치 추가"""
    try:
        matches_sheet = get_worksheet("matches")
        mp_sheet = get_worksheet("match_players")
        
        next_match_id = _get_next_id(matches_sheet)
        matches_sheet.append_row([
            next_match_id, match_type, host, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), winning_team
        ])
        
        next_mp_id = _get_next_id(mp_sheet)
        mp_rows = []
        for i, p in enumerate(players_data):
            mp_rows.append([next_mp_id + i, next_match_id, p[0], p[1], p[2], p[3]])
            
        if mp_rows:
            mp_sheet.append_rows(mp_rows)
            
        clear_cache()
        
        if match_type == "NORMAL" and winning_team not in ["아직 모름", ""]:
            _apply_match_bonus(players_data, winning_team)
        
        logger.info(f"매치 추가 완료: {match_type} - {host}")
        return True
    except Exception as e:
        logger.error(f"매치 추가 실패: {e}")
        return False

def update_match_winner(match_id: int, new_winning_team: str) -> bool:
    """매치 승리팀 업데이트"""
    try:
        matches_sheet = get_worksheet("matches")
        mp_sheet = get_worksheet("match_players")
        
        matches = _get_all_matches_raw()
        match = next((m for m in matches if str(m['id']) == str(match_id)), None)
        
        if match:
            old_winning_team = match.get('winning_team', '')
            
            if match.get('match_type') == 'NORMAL' and old_winning_team not in ["아직 모름", ""]:
                mps = [mp for mp in _get_all_match_players_raw() if str(mp.get('match_id')) == str(match_id)]
                players_data_rollback = [(mp['user_id'], mp['team_name'], mp['role'], mp['points_spent']) for mp in mps]
                _rollback_match_bonus(players_data_rollback, old_winning_team)
                
            cell = matches_sheet.find(str(match_id), in_column=1)
            if cell:
                matches_sheet.update_cell(cell.row, 5, new_winning_team)
                
            if match.get('match_type') == 'NORMAL' and new_winning_team not in ["아직 모름", ""]:
                mps = [mp for mp in _get_all_match_players_raw() if str(mp.get('match_id')) == str(match_id)]
                players_data = [(mp['user_id'], mp['team_name'], mp['role'], mp['points_spent']) for mp in mps]
                _apply_match_bonus(players_data, new_winning_team)
                
            clear_cache()
            logger.info(f"매치 승리팀 업데이트 완료: Match {match_id} -> {new_winning_team}")
            return True
        return False
    except Exception as e:
        logger.error(f"매치 승리팀 업데이트 실패: {e}")
        return False

def _apply_match_bonus(players_data: List[tuple], winning_team: str) -> None:
    """매치 보너스 적용 (승리팀/패배팀 MMR 증감)"""
    from utils.tier_fetcher import calculate_mmr_delta, calculate_clan_tier

    users_sheet = get_worksheet("users")
    users = get_all_users()
    user_dict = {str(u['id']): u for u in users}
    
    updates = []
    for p in players_data:
        uid = str(p[0])
        team_name = p[1]
        if uid in user_dict:
            u = user_dict[uid]
            base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
            
            effective_tier = calculate_clan_tier(base_score)
            
            current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus', '')) != '' else 0)
            
            if team_name == winning_team:
                bonus_change = calculate_mmr_delta(effective_tier, is_win=True)
                current_bonus += bonus_change
            else:
                bonus_change = calculate_mmr_delta(effective_tier, is_win=False)
                current_bonus -= bonus_change
                
            current_bonus = max(-base_score, current_bonus)
                
            cell_row = [idx + 2 for idx, val in enumerate(users) if str(val['id']) == uid][0]
            updates.append({'range': f"M{cell_row}", 'values': [[current_bonus]]})
                
    if updates:
        users_sheet.batch_update(updates)
        logger.info(f"매치 보너스 적용 완료: {len(updates)}명")

def _rollback_match_bonus(players_data: List[tuple], winning_team: str) -> None:
    """매치 보너스 롤백 (승리팀 변경 시 이전 보너스 취소)"""
    from utils.tier_fetcher import calculate_mmr_delta, calculate_clan_tier

    users_sheet = get_worksheet("users")
    users = get_all_users()
    user_dict = {str(u['id']): u for u in users}
    
    updates = []
    for p in players_data:
        uid = str(p[0])
        team_name = p[1]
        if uid in user_dict:
            u = user_dict[uid]
            base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
            
            effective_tier = calculate_clan_tier(base_score)
            
            current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus', '')) != '' else 0)
            
            if team_name == winning_team:
                bonus_change = calculate_mmr_delta(effective_tier, is_win=True)
                current_bonus -= bonus_change
            else:
                bonus_change = calculate_mmr_delta(effective_tier, is_win=False)
                current_bonus += bonus_change
                
            current_bonus = max(-base_score, current_bonus)
                
            cell_row = [idx + 2 for idx, val in enumerate(users) if str(val['id']) == uid][0]
            updates.append({'range': f"M{cell_row}", 'values': [[current_bonus]]})
                
    if updates:
        users_sheet.batch_update(updates)
        logger.info(f"매치 보너스 롤백 완료: {len(updates)}명")

@st.cache_data(ttl=CACHE_TTL)
def get_user_stats() -> Dict[int, Dict[str, int]]:
    """사용자별 내전 통계 조회"""
    users = get_all_users()
    matches = _get_all_matches_raw()
    mp_sheet = _get_all_match_players_raw()
    
    stats = {}
    for u in users:
        if u.get('status') == 'APPROVED':
            stats[int(u['id'])] = {'total': 0, 'wins': 0, 'win_rate': 0}
            
    valid_matches = {str(m['id']): m['winning_team'] for m in matches if m.get('match_type') in ['NORMAL', 'AUCTION'] and m.get('winning_team') not in ['', '아직 모름']}
    
    for mp in mp_sheet:
        uid = int(mp['user_id'])
        mid = str(mp['match_id'])
        if uid in stats and mid in valid_matches:
            stats[uid]['total'] += 1
            if mp['team_name'] == valid_matches[mid]:
                stats[uid]['wins'] += 1
                
    for uid in stats:
        t = stats[uid]['total']
        w = stats[uid]['wins']
        stats[uid]['win_rate'] = round((w / t * 100), 1) if t > 0 else 0
        
    return stats

@st.cache_data(ttl=CACHE_TTL)
def get_auction_points_by_user() -> Dict[int, int]:
    """사용자별 경매 내전 포인트 조회"""
    matches = _get_all_matches_raw()
    mps = _get_all_match_players_raw()
    
    # 2026년 7월 15일 21시 (패치 배포 시점)
    cutoff_date = datetime(2026, 7, 15, 21, 0, 0)
    
    points = {}
    for match in matches:
        if match.get('match_type') == 'AUCTION' and match.get('winning_team') not in ["", "아직 모름"]:
            all_match_mps = [mp for mp in mps if str(mp.get('match_id')) == str(match['id'])]
            num_players = len(all_match_mps)
            
            points_to_award = 0
            if num_players >= 40:
                points_to_award = 5  # 1 Medal
            elif num_players >= 30:
                points_to_award = 1  # 1 Star
            else:
                # 30인 미만 내전의 경우
                match_date_str = match.get('match_date', '')
                if match_date_str:
                    try:
                        match_date = datetime.strptime(match_date_str, "%Y-%m-%d %H:%M:%S")
                        if match_date < cutoff_date:
                            points_to_award = 1  # 과거 20인 내전 우승 별 유지
                    except ValueError:
                        pass
            
            if points_to_award > 0:
                winning_mps = [mp for mp in all_match_mps if mp['team_name'] == match['winning_team']]
                for mp in winning_mps:
                    uid = int(mp['user_id'])
                    points[uid] = points.get(uid, 0) + points_to_award
                    
    return points

