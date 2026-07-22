import gspread
import streamlit as st
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple

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
                u.get('main_position', ''), u.get('sub_position', ''),
                int(u.get('manual_cats', 0) if str(u.get('manual_cats', '')) != '' else 0)
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

def update_manual_match_bonus(user_id: int, manual_bonus: int) -> bool:
    """수동 내전 보너스 증감치 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update_cell(cell.row, 13, manual_bonus) # M열(13)이 match_bonus
            clear_cache()
            logger.info(f"수동 내전 보너스 업데이트 완료: ID {user_id} -> {manual_bonus}")
            return True
        return False
    except Exception as e:
        logger.error(f"수동 내전 보너스 업데이트 실패: {e}")
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

def update_manual_cats(user_id: int, cats: int) -> bool:
    """수동 고양이 포인트 업데이트"""
    try:
        users_sheet = get_worksheet("users")
        rows = users_sheet.get_all_values()
        headers = rows[0]
        
        col_cats = headers.index('manual_cats') + 1 if 'manual_cats' in headers else 16
        
        if 'manual_cats' not in headers:
            users_sheet.update_cell(1, 16, 'manual_cats')
            col_cats = 16

        cell = users_sheet.find(str(user_id), in_column=1)
        if cell:
            users_sheet.update_cell(cell.row, col_cats, cats)
            clear_cache()
            logger.info(f"수동 고양이 포인트 업데이트 완료: ID {user_id} -> {cats}")
            return True
        return False
    except Exception as e:
        logger.error(f"수동 고양이 포인트 업데이트 실패: {e}")
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
            
        if match_to_delete and match_to_delete.get('match_type') == 'NORMAL' and match_to_delete.get('winning_team') not in ['아직 모름', '']:
            clear_cache()
            recalculate_all_match_bonuses()
        else:
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
    
    valid_records = [r for r in records if str(r.get('id', '')).isdigit()]
    return [(int(r['id']), r.get('match_type', ''), r.get('host', ''), r.get('match_date', ''), r.get('winning_team', '')) for r in valid_records]

@st.cache_data(ttl=CACHE_TTL)
def get_match_players(match_id: int) -> List[tuple]:
    """특정 매치의 참가자 목록 조회"""
    mps = [mp for mp in _get_all_match_players_raw() if str(mp.get('match_id')) == str(match_id)]
    users = {str(u['id']): u for u in get_all_users()}
    
    result = []
    for mp in mps:
        uid = str(mp.get('user_id', ''))
        if uid in users:
            u = users[uid]
            
            p_score = u.get('power_score', 0)
            m_score = u.get('manual_score', -1)
            p_spent = mp.get('points_spent', 0)
            
            p_score_val = int(p_score) if str(p_score).lstrip('-').isdigit() else 0
            m_score_val = int(m_score) if str(m_score).lstrip('-').isdigit() else -1
            p_spent_val = int(p_spent) if str(p_spent).lstrip('-').isdigit() else 0
            
            result.append((
                mp.get('team_name', ''), mp.get('role', ''), u.get('riot_id', ''), u.get('tag_line', ''), 
                p_score_val, m_score_val, p_spent_val, 
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
            recalculate_all_match_bonuses()
        
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
            cell = matches_sheet.find(str(match_id), in_column=1)
            if cell:
                matches_sheet.update_cell(cell.row, 5, new_winning_team)
                
            if match.get('match_type') == 'NORMAL':
                clear_cache()
                recalculate_all_match_bonuses()
            else:
                clear_cache()
            logger.info(f"매치 승리팀 업데이트 완료: Match {match_id} -> {new_winning_team}")
            return True
        return False
    except Exception as e:
        logger.error(f"매치 승리팀 업데이트 실패: {e}")
        return False

def recalculate_all_match_bonuses() -> None:
    """모든 내전 이력을 시간순으로 다시 계산하여 점수를 소급 적용합니다."""
    users_sheet = get_worksheet("users")
    headers = users_sheet.get_all_values()[0]
    if 'last_win_bonus' not in headers:
        users_sheet.update_cell(1, len(headers) + 1, 'last_win_bonus')
        headers.append('last_win_bonus')

    col_match_bonus = headers.index('match_bonus') + 1 if 'match_bonus' in headers else 13
    col_last_win = headers.index('last_win_bonus') + 1

    users = get_all_users()
    matches = _get_all_matches_raw()
    match_players = _get_all_match_players_raw()

    try:
        matches = sorted(matches, key=lambda x: str(x.get('match_date', '')))
    except Exception:
        pass

    user_state = {}
    for idx, u in enumerate(users):
        uid = str(u['id'])
        base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
        user_state[uid] = {
            'row': idx + 2,
            'base_score': base_score,
            'match_bonus': 0,
            'last_win_bonus': 0
        }

    valid_matches = [m for m in matches if m.get('match_type') == 'NORMAL' and m.get('winning_team') not in ["", "아직 모름"]]

    for match in valid_matches:
        mid = str(match['id'])
        winning_team = match['winning_team']
        mps = [mp for mp in match_players if str(mp['match_id']) == mid]

        for mp in mps:
            uid = str(mp['user_id'])
            if uid in user_state:
                state = user_state[uid]
                current_score = state['base_score'] + state['match_bonus']
                
                if mp['team_name'] == winning_team:
                    gain = int(current_score * 0.04)
                    state['match_bonus'] += gain
                    state['last_win_bonus'] = gain
                else:
                    loss = state['last_win_bonus']
                    state['match_bonus'] = max(0, state['match_bonus'] - loss)

    updates = []
    def col_to_letter(col):
        letter = ''
        while col > 0:
            col, remainder = divmod(col - 1, 26)
            letter = chr(65 + remainder) + letter
        return letter

    bonus_letter = col_to_letter(col_match_bonus)
    last_win_letter = col_to_letter(col_last_win)

    for uid, state in user_state.items():
        updates.append({'range': f"{bonus_letter}{state['row']}", 'values': [[state['match_bonus']]]})
        updates.append({'range': f"{last_win_letter}{state['row']}", 'values': [[state['last_win_bonus']]]})

    if updates:
        users_sheet.batch_update(updates)
        logger.info(f"전체 매치 보너스 재계산 완료: {len(updates)//2}명")

@st.cache_data(ttl=CACHE_TTL)
def get_historical_match_deltas() -> Dict[str, Dict[str, int]]:
    """
    모든 내전 이력을 순회하며, 각 매치별로 유저가 얻거나 잃은 실제 점수(delta)를 계산하여 반환합니다.
    반환 형태: { match_id (str): { user_id (str): delta_score (int) } }
    """
    users = get_all_users()
    matches = _get_all_matches_raw()
    match_players = _get_all_match_players_raw()

    try:
        matches = sorted(matches, key=lambda x: str(x.get('match_date', '')))
    except Exception:
        pass

    user_state = {}
    for u in users:
        uid = str(u['id'])
        base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
        user_state[uid] = {
            'base_score': base_score,
            'match_bonus': 0,
            'last_win_bonus': 0
        }

    valid_matches = [m for m in matches if m.get('match_type') == 'NORMAL' and m.get('winning_team') not in ["", "아직 모름"]]
    
    deltas = {}

    for match in valid_matches:
        mid = str(match['id'])
        winning_team = match['winning_team']
        mps = [mp for mp in match_players if str(mp['match_id']) == mid]
        
        deltas[mid] = {}

        for mp in mps:
            uid = str(mp['user_id'])
            if uid in user_state:
                state = user_state[uid]
                current_score = state['base_score'] + state['match_bonus']
                
                if mp['team_name'] == winning_team:
                    gain = int(current_score * 0.04)
                    deltas[mid][uid] = gain
                    state['match_bonus'] += gain
                    state['last_win_bonus'] = gain
                else:
                    loss = state['last_win_bonus']
                    actual_loss = min(loss, state['match_bonus']) # 차감되는 실제 양
                    deltas[mid][uid] = -actual_loss
                    state['match_bonus'] -= actual_loss

    return deltas

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
def get_auction_points_by_user() -> Tuple[Dict[int, int], Dict[int, int]]:
    """사용자별 경매 내전 포인트(별/메달/트로피용)와 20인 승리 횟수(고양이용) 조회"""
    matches = _get_all_matches_raw()
    mps = _get_all_match_players_raw()
    
    # 2026년 7월 15일 21시 (패치 배포 시점)
    cutoff_date = datetime(2026, 7, 15, 21, 0, 0)
    # 2026년 7월 21일 21시 (고양이 보상 도입 시점)
    cat_cutoff_date = datetime(2026, 7, 21, 21, 0, 0)
    
    points = {}
    cats = {}
    for match in matches:
        if match.get('match_type') == 'AUCTION' and match.get('winning_team') not in ["", "아직 모름"]:
            all_match_mps = [mp for mp in mps if str(mp.get('match_id')) == str(match['id'])]
            num_players = len(all_match_mps)
            
            points_to_award = 0
            cats_to_award = 0
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
                        elif match_date >= cat_cutoff_date and num_players >= 20:
                            cats_to_award = 1    # 현재 20인 내전 우승 고양이 지급
                    except ValueError:
                        pass
            
            if points_to_award > 0 or cats_to_award > 0:
                winning_mps = [mp for mp in all_match_mps if mp['team_name'] == match['winning_team']]
                for mp in winning_mps:
                    uid = int(mp['user_id'])
                    if points_to_award > 0:
                        points[uid] = points.get(uid, 0) + points_to_award
                    if cats_to_award > 0:
                        cats[uid] = cats.get(uid, 0) + cats_to_award
                    
    return points, cats

