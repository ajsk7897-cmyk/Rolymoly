import gspread

SPREADSHEET_ID = "1HI0dwaA6HJV9g--lpOpprSO_UoFhFXUleFhI4ur2-44"

def init_db():
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # Check and create 'users' sheet
    try:
        sh.worksheet("users")
        print("users sheet exists")
    except gspread.exceptions.WorksheetNotFound:
        users_sheet = sh.add_worksheet(title="users", rows="1000", cols="20")
        users_sheet.append_row([
            "id", "riot_id", "tag_line", "birthdate", "status", "solo_tier", 
            "flex_tier", "power_score", "manual_score", "manual_stars", 
            "is_admin", "join_date", "match_bonus"
        ])
        print("created users sheet")

    # Check and create 'matches' sheet
    try:
        sh.worksheet("matches")
        print("matches sheet exists")
    except gspread.exceptions.WorksheetNotFound:
        matches_sheet = sh.add_worksheet(title="matches", rows="1000", cols="20")
        matches_sheet.append_row([
            "id", "match_type", "host", "match_date", "winning_team"
        ])
        print("created matches sheet")

    # Check and create 'match_players' sheet
    try:
        sh.worksheet("match_players")
        print("match_players sheet exists")
    except gspread.exceptions.WorksheetNotFound:
        mp_sheet = sh.add_worksheet(title="match_players", rows="1000", cols="20")
        mp_sheet.append_row([
            "id", "match_id", "user_id", "team_name", "role", "points_spent"
        ])
        print("created match_players sheet")

    # Check and create 'settings' sheet
    try:
        sh.worksheet("settings")
        print("settings sheet exists")
    except gspread.exceptions.WorksheetNotFound:
        settings_sheet = sh.add_worksheet(title="settings", rows="100", cols="2")
        settings_sheet.append_row(["key", "value"])
        settings_sheet.append_row(["admin_password", "admin1234"])
        print("created settings sheet")

if __name__ == "__main__":
    init_db()
