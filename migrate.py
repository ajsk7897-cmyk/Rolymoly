import sqlite3
import gspread
import os

DB_NAME = "clan.db"
SPREADSHEET_ID = "1HI0dwaA6HJV9g--lpOpprSO_UoFhFXUleFhI4ur2-44"

def migrate():
    if not os.path.exists(DB_NAME):
        print("No clan.db found, skipping migration.")
        return
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # 1. Migrate Users
    print("Migrating users...")
    c.execute("SELECT id, riot_id, tag_line, birthdate, status, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, join_date FROM users")
    users = c.fetchall()
    if users:
        users_sheet = sh.worksheet("users")
        rows = []
        for u in users:
            # u: id, riot_id, tag_line, birthdate, status, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, join_date
            rows.append(list(u) + [0]) # add match_bonus = 0
        users_sheet.append_rows(rows)
        
    # 2. Migrate Matches
    print("Migrating matches...")
    c.execute("SELECT id, match_type, host, match_date, winning_team FROM matches")
    matches = c.fetchall()
    if matches:
        matches_sheet = sh.worksheet("matches")
        matches_sheet.append_rows([list(m) for m in matches])
        
    # 3. Migrate Match Players
    print("Migrating match players...")
    c.execute("SELECT id, match_id, user_id, team_name, role, points_spent FROM match_players")
    mps = c.fetchall()
    if mps:
        mp_sheet = sh.worksheet("match_players")
        # gspread limit is around 100-200 rows per batch if large, but we can try append_rows
        # to avoid payload size limit.
        mp_sheet.append_rows([list(mp) for mp in mps])
        
    print("Migration complete!")
    conn.close()

if __name__ == "__main__":
    migrate()
