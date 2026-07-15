import gspread
import streamlit as st
from datetime import datetime

SPREADSHEET_ID = "1HI0dwaA6HJV9g--lpOpprSO_UoFhFXUleFhI4ur2-44"

@st.cache_resource
def get_gspread_client():
    import json
    try:
        if "gcp_service_account" in st.secrets:
            # Streamlit Cloud Secrets 사용
            secret_val = st.secrets["gcp_service_account"]
            if isinstance(secret_val, str):
                creds_dict = json.loads(secret_val)
            else:
                creds_dict = dict(secret_val)
            return gspread.service_account_from_dict(creds_dict)
    except Exception:
        pass
        
    # 로컬 환경 (credentials.json 파일 사용)
    return gspread.service_account(filename="credentials.json")

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

@st.cache_data(ttl=60)
def get_all_settings():
    settings_sheet = get_worksheet("settings")
    records = settings_sheet.get_all_records()
    return records

def get_admin_password():
    records = get_all_settings()
    for row in records:
        if row['key'] == 'admin_password':
            return row['value']
    return 'admin1234'

def set_admin_password(new_password):
    settings_sheet = get_worksheet("settings")
    cell = settings_sheet.find("admin_password", in_column=1)
    if cell:
        settings_sheet.update_cell(cell.row, cell.col + 1, new_password)
    clear_cache()

def _get_next_id(sheet):
    records = sheet.get_all_records()
    if not records:
        return 1
    ids = [int(r['id']) for r in records if str(r['id']).isdigit()]
    return max(ids) + 1 if ids else 1

def add_user(riot_id, tag_line, birthdate, main_position='', sub_position=''):
    users_sheet = get_worksheet("users")
    next_id = _get_next_id(users_sheet)
    users_sheet.append_row([
        next_id, riot_id, f"'{tag_line}", f"'{birthdate}", "PENDING", "Unranked", "Unranked", 0, -1, 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, main_position, sub_position
    ], value_input_option='USER_ENTERED')
    clear_cache()

@st.cache_data(ttl=60)
def get_all_users():
    users_sheet = get_worksheet("users")
    rows = users_sheet.get_all_values()
    if not rows or len(rows) < 2:
        return []
    headers = rows[0]
    records = []
    for row in rows[1:]:
        record = {}
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) else ''
            if val.startswith("'"):
                val = val[1:]
            record[h] = val
        records.append(record)
    return records

def get_pending_users():
    users = get_all_users()
    pending = []
    for u in users:
        if u['status'] == 'PENDING':
            pending.append((u['id'], u['riot_id'], u['tag_line'], u['birthdate']))
    return pending

def get_all_approved_users():
    users = get_all_users()
    approved = []
    for u in users:
        if u['status'] == 'APPROVED':
            approved.append((
                int(u['id']), u['riot_id'], u['tag_line'], u['solo_tier'], 
                u['flex_tier'], int(u['power_score']), int(u['manual_score']), 
                int(u['manual_stars']), int(u['is_admin']), int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0),
                u.get('main_position', ''), u.get('sub_position', '')
            ))
    return approved

def approve_user(user_id, solo_tier, flex_tier, power_score):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.update(f"E{cell.row}:H{cell.row}", [["APPROVED", solo_tier, flex_tier, power_score]])
        clear_cache()

def update_user_tier_info(user_id, solo_tier, flex_tier, power_score):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.update(f"F{cell.row}:H{cell.row}", [[solo_tier, flex_tier, power_score]])
        clear_cache()

def batch_update_user_tiers(tier_updates):
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

def reject_user(user_id):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.delete_rows(cell.row)
        clear_cache()

def update_manual_score(user_id, manual_score):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.update_cell(cell.row, 9, manual_score)
        clear_cache()

def update_user_positions(user_id, main_pos, sub_pos):
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

def update_manual_stars(user_id, stars):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.update_cell(cell.row, 10, stars)
        clear_cache()

def update_admin_role(user_id, is_admin):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.update_cell(cell.row, 11, is_admin)
        clear_cache()

def kick_user(user_id):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.update_cell(cell.row, 5, 'KICKED')
        clear_cache()

def delete_all_history():
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
            
    except Exception as e:
        print("Error resetting history", e)
    clear_cache()

def delete_match(match_id):
    matches_sheet = get_worksheet("matches")
    mp_sheet = get_worksheet("match_players")
    users_sheet = get_worksheet("users")
    
    matches = matches_sheet.get_all_records()
    match_to_delete = next((m for m in matches if str(m['id']) == str(match_id)), None)
    mps = mp_sheet.get_all_records()
    
    if match_to_delete and match_to_delete['match_type'] == 'NORMAL' and match_to_delete['winning_team'] not in ['아직 모름', '']:
        winning_team = match_to_delete['winning_team']
        users = get_all_users()
        user_dict = {str(u['id']): u for u in users}
        
        updates = []
        for mp in mps:
            if str(mp['match_id']) == str(match_id):
                uid = str(mp['user_id'])
                if uid in user_dict:
                    u = user_dict[uid]
                    import sys, os
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from utils.tier_fetcher import calculate_mmr_delta, calculate_clan_tier

                    base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
                    effective_tier = calculate_clan_tier(base_score)
                    current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
                    
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

@st.cache_data(ttl=60)
def get_matches():
    matches_sheet = get_worksheet("matches")
    records = matches_sheet.get_all_records()
    try:
        records = sorted(records, key=lambda x: str(x['match_date']), reverse=True)
    except:
        pass
    return [(int(r['id']), r['match_type'], r['host'], r['match_date'], r['winning_team']) for r in records]

@st.cache_data(ttl=60)
def get_match_players(match_id):
    mp_sheet = get_worksheet("match_players")
    users_sheet = get_worksheet("users")
    
    mps = [mp for mp in mp_sheet.get_all_records() if str(mp['match_id']) == str(match_id)]
    users = {str(u['id']): u for u in get_all_users()}
    
    result = []
    for mp in mps:
        uid = str(mp['user_id'])
        if uid in users:
            u = users[uid]
            result.append((
                mp['team_name'], mp['role'], u['riot_id'], u['tag_line'], 
                int(u['power_score']), int(u['manual_score']), int(mp['points_spent']), 
                int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
            ))
    return result

def add_match(match_type, host, winning_team, players_data):
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

def update_match_winner(match_id, new_winning_team):
    matches_sheet = get_worksheet("matches")
    mp_sheet = get_worksheet("match_players")
    
    matches = matches_sheet.get_all_records()
    match = next((m for m in matches if str(m['id']) == str(match_id)), None)
    
    if match:
        old_winning_team = match['winning_team']
        
        if match['match_type'] == 'NORMAL' and old_winning_team not in ["아직 모름", ""]:
            mps = [mp for mp in mp_sheet.get_all_records() if str(mp['match_id']) == str(match_id)]
            players_data_rollback = [(mp['user_id'], mp['team_name'], mp['role'], mp['points_spent']) for mp in mps]
            _rollback_match_bonus(players_data_rollback, old_winning_team)
            
        cell = matches_sheet.find(str(match_id), in_column=1)
        if cell:
            matches_sheet.update_cell(cell.row, 5, new_winning_team)
            
        if match['match_type'] == 'NORMAL' and new_winning_team not in ["아직 모름", ""]:
            mps = [mp for mp in mp_sheet.get_all_records() if str(mp['match_id']) == str(match_id)]
            players_data = [(mp['user_id'], mp['team_name'], mp['role'], mp['points_spent']) for mp in mps]
            _apply_match_bonus(players_data, new_winning_team)
            
        clear_cache()

def _apply_match_bonus(players_data, winning_team):
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
            
            current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
            
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

def _rollback_match_bonus(players_data, winning_team):
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
            
            current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
            
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

@st.cache_data(ttl=60)
def get_user_stats():
    users = get_all_users()
    
    try:
        matches = get_worksheet("matches").get_all_records()
    except Exception:
        matches = []
        
    try:
        mp_sheet = get_worksheet("match_players").get_all_records()
    except Exception:
        mp_sheet = []
    
    stats = {}
    for u in users:
        if u['status'] == 'APPROVED':
            stats[int(u['id'])] = {'total': 0, 'wins': 0, 'win_rate': 0}
            
    valid_matches = {str(m['id']): m['winning_team'] for m in matches if m['match_type'] == 'NORMAL' and m['winning_team'] not in ['', '아직 모름']}
    
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

@st.cache_data(ttl=60)
def get_auction_points_by_user():
    matches_sheet = get_worksheet("matches")
    mp_sheet = get_worksheet("match_players")
    
    matches = matches_sheet.get_all_records()
    mps = mp_sheet.get_all_records()
    
    # 2026년 7월 15일 21시 (패치 배포 시점)
    cutoff_date = datetime(2026, 7, 15, 21, 0, 0)
    
    points = {}
    for match in matches:
        if match['match_type'] == 'AUCTION' and match['winning_team'] not in ["", "아직 모름"]:
            all_match_mps = [mp for mp in mps if str(mp['match_id']) == str(match['id'])]
            num_players = len(all_match_mps)
            
            points_to_award = 0
            if num_players >= 40:
                points_to_award = 5  # 1 Medal
            elif num_players >= 30:
                points_to_award = 1  # 1 Star
            else:
                # 30인 미만 내전의 경우
                match_date_str = match.get('date', '')
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

init_db()
