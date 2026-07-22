import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

def col_to_letter(col):
    letter = ''
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        letter = chr(65 + remainder) + letter
    return letter

def main():
    print("Fetching data...")
    matches = database._get_all_matches_raw()
    match_players = database._get_all_match_players_raw()
    users = database.get_all_users()
    users_sheet = database.get_worksheet("users")

    # Sort matches chronologically
    try:
        matches = sorted(matches, key=lambda x: str(x.get('match_date', '')))
    except Exception as e:
        print(f"Sorting error: {e}")

    # Ensure last_win_bonus column exists
    headers = users_sheet.get_all_values()[0]
    if 'last_win_bonus' not in headers:
        users_sheet.update_cell(1, len(headers) + 1, 'last_win_bonus')
        headers.append('last_win_bonus')

    col_match_bonus = headers.index('match_bonus') + 1 if 'match_bonus' in headers else 13
    col_last_win = headers.index('last_win_bonus') + 1

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
    print(f"Found {len(valid_matches)} valid normal matches.")

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

    print("Preparing batch update...")
    updates = []
    bonus_letter = col_to_letter(col_match_bonus)
    last_win_letter = col_to_letter(col_last_win)

    for uid, state in user_state.items():
        updates.append({'range': f"{bonus_letter}{state['row']}", 'values': [[state['match_bonus']]]})
        updates.append({'range': f"{last_win_letter}{state['row']}", 'values': [[state['last_win_bonus']]]})

    if updates:
        users_sheet.batch_update(updates)
        database.clear_cache()
        print(f"Successfully updated {len(updates)//2} users.")
    else:
        print("No updates needed.")

if __name__ == "__main__":
    main()
