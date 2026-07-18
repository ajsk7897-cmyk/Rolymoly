import database
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def fix_duplicates():
    users = database.get_all_users()
    normalized_map = {}
    
    for u in users:
        norm_name = u['riot_id'].lower().replace(' ', '') + '#' + u['tag_line'].lower().replace(' ', '')
        if norm_name not in normalized_map:
            normalized_map[norm_name] = []
        normalized_map[norm_name].append(u)
        
    mp_sheet = database.get_worksheet("match_players")
    mps = mp_sheet.get_all_records()
    
    updates = []
    
    for name, u_list in normalized_map.items():
        if len(u_list) > 1:
            approved_users = [u for u in u_list if u['status'] == 'APPROVED']
            if not approved_users:
                continue
            
            target_uid = str(approved_users[0]['id'])
            kicked_uids = [str(u['id']) for u in u_list if u['status'] != 'APPROVED']
            
            for idx, mp in enumerate(mps):
                if str(mp['user_id']) in kicked_uids:
                    print(f"Migrating match {mp['match_id']} from user {mp['user_id']} to {target_uid}")
                    # cell_row is idx + 2 (1 for header, 1 for 0-index)
                    # user_id is column 3 (C)
                    updates.append({'range': f"C{idx + 2}", 'values': [[target_uid]]})
                    
    if updates:
        print(f"Updating {len(updates)} match_player records...")
        mp_sheet.batch_update(updates)
    else:
        print("No match_player records needed migration.")

if __name__ == "__main__":
    fix_duplicates()
