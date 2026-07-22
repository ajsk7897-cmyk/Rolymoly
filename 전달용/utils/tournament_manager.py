import json
import os
import random
import itertools
import time

TOURNAMENTS_FILE = "tournaments.json"

def _load_data():
    if not os.path.exists(TOURNAMENTS_FILE):
        return []
    try:
        with open(TOURNAMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def _save_data(data):
    with open(TOURNAMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_session(host_name, teams, players_data, match_format):
    """
    teams: list of team dicts (id, name, points, members)
    players_data: list of tuples (user_id, team_name, role, points_spent)
    match_format: "LEAGUE" or "TOURNAMENT"
    """
    sessions = _load_data()
    team_names = [t['name'] for t in teams]
    random.shuffle(team_names)
    
    session = {
        "session_id": str(int(time.time())),
        "host": host_name,
        "format": match_format,
        "teams": teams,
        "players_data": players_data,
        "status": "ONGOING"
    }
    
    if match_format == "LEAGUE":
        matches = []
        match_id = 1
        for t1, t2 in itertools.combinations(team_names, 2):
            matches.append({
                "id": match_id,
                "team1": t1,
                "team2": t2,
                "winner": None
            })
            match_id += 1
        session["matches"] = matches
        
        standings = {}
        for t in team_names:
            standings[t] = {"wins": 0, "losses": 0, "points": 0}
        session["standings"] = standings
        
    elif match_format == "TOURNAMENT":
        # 4 teams or 6 teams
        n = len(team_names)
        rounds = []
        
        if n == 4:
            # Semi-finals
            r1 = [
                {"id": "R1_1", "team1": team_names[0], "team2": team_names[1], "winner": None, "is_bye": False},
                {"id": "R1_2", "team1": team_names[2], "team2": team_names[3], "winner": None, "is_bye": False}
            ]
            # Final
            r2 = [
                {"id": "R2_1", "team1": None, "team2": None, "winner": None, "is_bye": False}
            ]
            rounds = [r1, r2]
        elif n == 6:
            # Quarter-finals (2 matches, 2 byes)
            # team_names[0] and team_names[1] get byes
            r1 = [
                {"id": "R1_1", "team1": team_names[0], "team2": None, "winner": team_names[0], "is_bye": True},
                {"id": "R1_2", "team1": team_names[1], "team2": None, "winner": team_names[1], "is_bye": True},
                {"id": "R1_3", "team1": team_names[2], "team2": team_names[3], "winner": None, "is_bye": False},
                {"id": "R1_4", "team1": team_names[4], "team2": team_names[5], "winner": None, "is_bye": False}
            ]
            # Semi-finals
            r2 = [
                {"id": "R2_1", "team1": team_names[0], "team2": None, "winner": None, "is_bye": False}, # team_names[0] vs winner of R1_3
                {"id": "R2_2", "team1": team_names[1], "team2": None, "winner": None, "is_bye": False}  # team_names[1] vs winner of R1_4
            ]
            # Final
            r3 = [
                {"id": "R3_1", "team1": None, "team2": None, "winner": None, "is_bye": False}
            ]
            rounds = [r1, r2, r3]
            
        session["rounds"] = rounds
        
    elif match_format == "GROUP_STAGE":
        half = len(team_names) // 2
        group_A_teams = team_names[:half]
        group_B_teams = team_names[half:]
        
        matches = []
        match_id = 1
        for t1, t2 in itertools.combinations(group_A_teams, 2):
            matches.append({"id": f"A_{match_id}", "group": "A", "team1": t1, "team2": t2, "winner": None})
            match_id += 1
            
        match_id = 1
        for t1, t2 in itertools.combinations(group_B_teams, 2):
            matches.append({"id": f"B_{match_id}", "group": "B", "team1": t1, "team2": t2, "winner": None})
            match_id += 1
            
        session["matches"] = matches
        
        standings = {}
        for t in group_A_teams:
            standings[t] = {"group": "A", "wins": 0, "losses": 0, "points": 0}
        for t in group_B_teams:
            standings[t] = {"group": "B", "wins": 0, "losses": 0, "points": 0}
        session["standings"] = standings
        
        session["group_A_winner"] = None
        session["group_B_winner"] = None
        session["final_match"] = {"team1": None, "team2": None, "winner": None}
        
    sessions.append(session)
    _save_data(sessions)

def get_ongoing_sessions():
    sessions = _load_data()
    return [s for s in sessions if s.get("status") == "ONGOING"]

def update_league_match(session_id, match_id, winner_team_name):
    sessions = _load_data()
    for s in sessions:
        if s["session_id"] == session_id and s["format"] == "LEAGUE":
            for m in s["matches"]:
                if m["id"] == match_id:
                    old_winner = m["winner"]
                    
                    # Rollback old winner if any
                    if old_winner:
                        s["standings"][old_winner]["wins"] -= 1
                        s["standings"][old_winner]["points"] -= 3
                        loser = m["team1"] if m["team2"] == old_winner else m["team2"]
                        s["standings"][loser]["losses"] -= 1
                        
                    # Apply new winner
                    m["winner"] = winner_team_name
                    if winner_team_name:
                        s["standings"][winner_team_name]["wins"] += 1
                        s["standings"][winner_team_name]["points"] += 3
                        loser = m["team1"] if m["team2"] == winner_team_name else m["team2"]
                        s["standings"][loser]["losses"] += 1
                    break
    _save_data(sessions)

def update_tournament_match(session_id, round_idx, match_idx, winner_team_name):
    sessions = _load_data()
    for s in sessions:
        if s["session_id"] == session_id and s["format"] == "TOURNAMENT":
            rounds = s["rounds"]
            if round_idx < len(rounds):
                rounds[round_idx][match_idx]["winner"] = winner_team_name
                
                # Advance logic
                if round_idx + 1 < len(rounds):
                    next_round = rounds[round_idx + 1]
                    n_teams = len(s["teams"])
                    
                    if n_teams == 4:
                        if match_idx == 0:
                            next_round[0]["team1"] = winner_team_name
                        elif match_idx == 1:
                            next_round[0]["team2"] = winner_team_name
                    elif n_teams == 6:
                        if round_idx == 0:
                            # R1_3 winner goes to R2_1 team2
                            if match_idx == 2:
                                next_round[0]["team2"] = winner_team_name
                            # R1_4 winner goes to R2_2 team2
                            elif match_idx == 3:
                                next_round[1]["team2"] = winner_team_name
                        elif round_idx == 1:
                            # R2_1 -> R3_1 team1, R2_2 -> R3_1 team2
                            if match_idx == 0:
                                next_round[0]["team1"] = winner_team_name
                            elif match_idx == 1:
                                next_round[0]["team2"] = winner_team_name
    _save_data(sessions)

def update_group_match(session_id, match_id, winner_team_name):
    sessions = _load_data()
    for s in sessions:
        if s["session_id"] == session_id and s["format"] == "GROUP_STAGE":
            for m in s["matches"]:
                if m["id"] == match_id:
                    old_winner = m["winner"]
                    
                    # Rollback old winner if any
                    if old_winner:
                        s["standings"][old_winner]["wins"] -= 1
                        s["standings"][old_winner]["points"] -= 3
                        loser = m["team1"] if m["team2"] == old_winner else m["team2"]
                        s["standings"][loser]["losses"] -= 1
                        
                    # Apply new winner
                    m["winner"] = winner_team_name
                    if winner_team_name:
                        s["standings"][winner_team_name]["wins"] += 1
                        s["standings"][winner_team_name]["points"] += 3
                        loser = m["team1"] if m["team2"] == winner_team_name else m["team2"]
                        s["standings"][loser]["losses"] += 1
                    break
    _save_data(sessions)

def update_group_winners(session_id, group_a_winner, group_b_winner):
    sessions = _load_data()
    for s in sessions:
        if s["session_id"] == session_id and s["format"] == "GROUP_STAGE":
            s["group_A_winner"] = group_a_winner
            s["group_B_winner"] = group_b_winner
            
            if group_a_winner and group_b_winner:
                s["final_match"]["team1"] = group_a_winner
                s["final_match"]["team2"] = group_b_winner
                
                old_winner = s["final_match"].get("winner")
                if old_winner and old_winner not in [group_a_winner, group_b_winner]:
                    s["final_match"]["winner"] = None
            else:
                s["final_match"]["team1"] = None
                s["final_match"]["team2"] = None
                s["final_match"]["winner"] = None
            break
    _save_data(sessions)

def update_final_match(session_id, winner_team_name):
    sessions = _load_data()
    for s in sessions:
        if s["session_id"] == session_id and s["format"] == "GROUP_STAGE":
            s["final_match"]["winner"] = winner_team_name
            break
    _save_data(sessions)

def complete_session(session_id, final_winner):
    sessions = _load_data()
    target_session = None
    for s in sessions:
        if s["session_id"] == session_id:
            s["status"] = "COMPLETED"
            s["final_winner"] = final_winner
            target_session = s
            break
    _save_data(sessions)
    return target_session
