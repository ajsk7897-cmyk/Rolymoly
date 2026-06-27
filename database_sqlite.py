import sqlite3
from datetime import datetime

DB_NAME = "clan.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            riot_id TEXT,
            tag_line TEXT,
            birthdate TEXT,
            status TEXT DEFAULT 'PENDING',
            solo_tier TEXT DEFAULT 'Unranked',
            flex_tier TEXT DEFAULT 'Unranked',
            power_score INTEGER DEFAULT 0,
            manual_score INTEGER DEFAULT -1,
            manual_stars INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            main_position TEXT DEFAULT '',
            sub_position TEXT DEFAULT ''
        )
    ''')
    
    # Create matches table
    c.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_type TEXT,
            host TEXT,
            match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            winning_team TEXT
        )
    ''')
    
    # Create match_players table
    c.execute('''
        CREATE TABLE IF NOT EXISTS match_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            user_id INTEGER,
            team_name TEXT,
            role TEXT,
            points_spent INTEGER DEFAULT 0,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create settings table for dynamic config like admin password
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Insert default password if not exists
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', 'admin1234')")
    
    conn.commit()
    conn.close()

def get_admin_password():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'admin_password'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'admin1234'

def set_admin_password(new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE settings SET value = ? WHERE key = 'admin_password'", (new_password,))
    conn.commit()
    conn.close()

def add_user(riot_id, tag_line, birthdate, main_position='', sub_position=''):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (riot_id, tag_line, birthdate, main_position, sub_position) VALUES (?, ?, ?, ?, ?)",
              (riot_id, tag_line, birthdate, main_position, sub_position))
    conn.commit()
    conn.close()

def get_pending_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, riot_id, tag_line, birthdate FROM users WHERE status = 'PENDING'")
    users = c.fetchall()
    conn.close()
    return users

def approve_user(user_id, solo_tier, flex_tier, power_score):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET status = 'APPROVED', solo_tier = ?, flex_tier = ?, power_score = ?
        WHERE id = ?
    ''', (solo_tier, flex_tier, power_score, user_id))
    conn.commit()
    conn.close()

def reject_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_approved_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, main_position, sub_position 
        FROM users WHERE status = 'APPROVED'
    ''')
    users = c.fetchall()
    conn.close()
    return users

def update_manual_score(user_id, manual_score):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET manual_score = ? WHERE id = ?", (manual_score, user_id))
    conn.commit()
    conn.close()

def update_user_positions(user_id, main_pos, sub_pos):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET main_position = ?, sub_position = ? WHERE id = ?", (main_pos, sub_pos, user_id))
    conn.commit()
    conn.close()

def update_manual_stars(user_id, stars):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET manual_stars = ? WHERE id = ?", (stars, user_id))
    conn.commit()
    conn.close()

def update_admin_role(user_id, is_admin):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = ? WHERE id = ?", (is_admin, user_id))
    conn.commit()
    conn.close()

def kick_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    # To maintain history consistency, we might just set status to KICKED or delete.
    # We will delete them. If they have matches, their match records might be left dangling unless cascading delete, 
    # but since we want history, we should actually keep them in DB but mark as 'KICKED'.
    c.execute("UPDATE users SET status = 'KICKED' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def delete_all_history():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM match_players")
    c.execute("DELETE FROM matches")
    conn.commit()
    conn.close()

def add_match(match_type, host, winning_team, players_data):
    # players_data is a list of tuples: (user_id, team_name, role, points_spent)
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO matches (match_type, host, winning_team) VALUES (?, ?, ?)", 
              (match_type, host, winning_team))
    match_id = c.lastrowid
    
    for player in players_data:
        c.execute('''
            INSERT INTO match_players (match_id, user_id, team_name, role, points_spent)
            VALUES (?, ?, ?, ?, ?)
        ''', (match_id, player[0], player[1], player[2], player[3]))
        
    conn.commit()
    conn.close()

def get_matches():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, match_type, host, match_date, winning_team FROM matches ORDER BY match_date DESC")
    matches = c.fetchall()
    conn.close()
    return matches

def get_user_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT 
            u.id,
            COUNT(mp.id) as total_matches,
            SUM(CASE WHEN m.winning_team = mp.team_name THEN 1 ELSE 0 END) as wins
        FROM users u
        LEFT JOIN match_players mp ON u.id = mp.user_id
        LEFT JOIN matches m ON mp.match_id = m.id AND m.match_type = 'NORMAL' AND m.winning_team NOT IN ('', '아직 모름')
        WHERE u.status = 'APPROVED'
        GROUP BY u.id
    ''')
    rows = c.fetchall()
    conn.close()
    
    stats = {}
    for row in rows:
        uid, total, wins = row
        win_rate = round((wins / total * 100), 1) if total and total > 0 else 0
        stats[uid] = {'total': total or 0, 'wins': wins or 0, 'win_rate': win_rate}
    return stats

def get_match_players(match_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT mp.team_name, mp.role, u.riot_id, u.tag_line, u.power_score, u.manual_score, mp.points_spent
        FROM match_players mp
        JOIN users u ON mp.user_id = u.id
        WHERE mp.match_id = ?
    ''', (match_id,))
    players = c.fetchall()
    conn.close()
    return players

def get_auction_wins_by_user():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT mp.user_id, COUNT(*) as wins
        FROM matches m
        JOIN match_players mp ON m.id = mp.match_id AND m.winning_team = mp.team_name
        WHERE m.match_type = 'AUCTION'
        GROUP BY mp.user_id
    ''')
    wins = dict(c.fetchall())
    conn.close()
    return wins

def update_match_winner(match_id, winning_team):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE matches SET winning_team = ? WHERE id = ?", (winning_team, match_id))
    conn.commit()
    conn.close()

# Initialize immediately when imported if not exists
init_db()
