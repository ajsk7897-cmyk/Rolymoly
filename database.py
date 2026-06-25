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

def add_user(riot_id, tag_line, birthdate):
    users_sheet = get_worksheet("users")
    next_id = _get_next_id(users_sheet)
    users_sheet.append_row([
        next_id, riot_id, f"'{tag_line}", f"'{birthdate}", "PENDING", "Unranked", "Unranked", 0, -1, 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0
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
                int(u['manual_stars']), int(u['is_admin']), int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
            ))
    return approved

def approve_user(user_id, solo_tier, flex_tier, power_score):
    users_sheet = get_worksheet("users")
    cell = users_sheet.find(str(user_id), in_column=1)
    if cell:
        users_sheet.update(f"E{cell.row}:H{cell.row}", [["APPROVED", solo_tier, flex_tier, power_score]])
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
                    base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
                    bonus_change = int(base_score * 0.05)
                    current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
                    
                    if mp['team_name'] == winning_team:
                        current_bonus -= bonus_change # rollback win
                    else:
                        current_bonus += bonus_change # rollback loss
                        
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
            bonus_change = int(base_score * 0.05)
            current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
            
            if team_name == winning_team:
                current_bonus += bonus_change
            else:
                current_bonus -= bonus_change
                
            cell_row = [idx + 2 for idx, val in enumerate(users) if str(val['id']) == uid][0]
            updates.append({'range': f"M{cell_row}", 'values': [[current_bonus]]})
                
    if updates:
        users_sheet.batch_update(updates)

def _rollback_match_bonus(players_data, winning_team):
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
            bonus_change = int(base_score * 0.05)
            current_bonus = int(u.get('match_bonus', 0) if str(u.get('match_bonus')) != '' else 0)
            
            if team_name == winning_team:
                current_bonus -= bonus_change
            else:
                current_bonus += bonus_change
                
            cell_row = [idx + 2 for idx, val in enumerate(users) if str(val['id']) == uid][0]
            updates.append({'range': f"M{cell_row}", 'values': [[current_bonus]]})
                
    if updates:
        users_sheet.batch_update(updates)

@st.cache_data(ttl=60)
def get_auction_wins_by_user():
    matches_sheet = get_worksheet("matches")
    mp_sheet = get_worksheet("match_players")
    
    matches = matches_sheet.get_all_records()
    mps = mp_sheet.get_all_records()
    
    wins = {}
    for match in matches:
        if match['match_type'] == 'AUCTION' and match['winning_team'] not in ["", "아직 모름"]:
            match_mps = [mp for mp in mps if str(mp['match_id']) == str(match['id']) and mp['team_name'] == match['winning_team']]
            for mp in match_mps:
                uid = int(mp['user_id'])
                wins[uid] = wins.get(uid, 0) + 1
    return wins

init_db()
