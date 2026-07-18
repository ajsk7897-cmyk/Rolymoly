import sys
import os

# Ensure the app dir is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
from utils.tier_fetcher import calculate_mmr_delta, calculate_clan_tier

def recalculate_all_match_bonuses():
    print("Starting recalculation...")
    users_sheet = database.get_worksheet("users")
    users = database.get_all_users()
    
    # 1. Reset all match_bonuses to 0 locally
    user_bonus_map = {str(u['id']): 0 for u in users}
    user_dict = {str(u['id']): u for u in users}
    
    matches_sheet = database.get_worksheet("matches")
    mp_sheet = database.get_worksheet("match_players")
    
    try:
        matches = matches_sheet.get_all_records()
    except Exception:
        matches = []
        
    try:
        mps = mp_sheet.get_all_records()
    except Exception:
        mps = []
        
    # Sort matches by ID to apply chronologically
    matches = sorted(matches, key=lambda x: int(x['id']))
    
    for match in matches:
        if match['match_type'] == 'NORMAL' and match['winning_team'] not in ["", "아직 모름"]:
            winning_team = match['winning_team']
            match_id = str(match['id'])
            
            # Find players for this match
            match_players = [mp for mp in mps if str(mp['match_id']) == match_id]
            
            for mp in match_players:
                uid = str(mp['user_id'])
                team_name = mp['team_name']
                
                if uid in user_dict:
                    u = user_dict[uid]
                    base_score = int(u['manual_score']) if int(u['manual_score']) != -1 else int(u['power_score'])
                    
                    effective_tier = calculate_clan_tier(base_score)
                    bonus_change = calculate_mmr_delta(effective_tier)
                    
                    if team_name == winning_team:
                        user_bonus_map[uid] += bonus_change
                    else:
                        user_bonus_map[uid] -= bonus_change
                    
                    # Cap at -base_score
                    user_bonus_map[uid] = max(-base_score, user_bonus_map[uid])

    # Batch update all users
    updates = []
    for idx, u in enumerate(users):
        uid = str(u['id'])
        if uid in user_bonus_map:
            cell_row = idx + 2
            # match_bonus is column M (13th column)
            updates.append({'range': f"M{cell_row}", 'values': [[user_bonus_map[uid]]]})
            
    if updates:
        users_sheet.batch_update(updates)
        print(f"Successfully updated match_bonus for {len(updates)} users.")
    else:
        print("No users to update.")

    database.clear_cache()
    
if __name__ == "__main__":
    recalculate_all_match_bonuses()
