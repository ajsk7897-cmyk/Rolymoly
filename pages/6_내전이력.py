import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
import importlib
importlib.reload(database)
from utils.tier_fetcher import calculate_mmr_delta, calculate_clan_tier
from utils.tournament_manager import get_ongoing_sessions, update_league_match, update_tournament_match, complete_session

st.set_page_config(page_title="내전 이력", page_icon="📜", layout="wide")

st.title("📜 내전 이력")

ongoing_sessions = get_ongoing_sessions()
if ongoing_sessions:
    st.subheader("🏁 진행 중인 경매내전 대회 (리그/토너먼트)")
    for s in ongoing_sessions:
        fmt_str = "리그 (풀리그)" if s["format"] == "LEAGUE" else "토너먼트 (승자 진출)"
        s_date = datetime.fromtimestamp(int(s["session_id"])).strftime("%y년 %m월 %d일 %H:%M")
        with st.expander(f"[{fmt_str}] {s_date} - 진행자: {s['host']}", expanded=True):
            if s["format"] == "LEAGUE":
                # Render Standings
                st.markdown("#### 🏆 조별 순위표")
                standings = s["standings"]
                # sort by points descending
                sorted_standings = sorted(standings.items(), key=lambda x: x[1]["points"], reverse=True)
                df_standings = pd.DataFrame([{
                    "순위": i+1,
                    "팀명": k,
                    "승점": v["points"],
                    "승": v["wins"],
                    "패": v["losses"]
                } for i, (k, v) in enumerate(sorted_standings)])
                st.dataframe(df_standings, use_container_width=True)
                
                # Render Matches
                st.markdown("#### ⚔️ 경기 일정 및 결과 입력")
                for m in s["matches"]:
                    col1, col2, col3, col4 = st.columns([3, 1, 3, 3])
                    with col1:
                        st.markdown(f"**{m['team1']}**")
                    with col2:
                        st.markdown("VS")
                    with col3:
                        st.markdown(f"**{m['team2']}**")
                    with col4:
                        winner_opts = ["진행 전", m["team1"], m["team2"]]
                        current_winner = m["winner"] if m["winner"] else "진행 전"
                        new_winner = st.selectbox(f"Match {m['id']} 승리팀", winner_opts, index=winner_opts.index(current_winner), key=f"lg_{s['session_id']}_{m['id']}", label_visibility="collapsed")
                        if new_winner != current_winner:
                            actual_winner = None if new_winner == "진행 전" else new_winner
                            update_league_match(s["session_id"], m["id"], actual_winner)
                            st.rerun()
            else:
                # TOURNAMENT
                st.markdown("#### 🏆 토너먼트 대진표")
                rounds = s["rounds"]
                for r_idx, r in enumerate(rounds):
                    st.markdown(f"**Round {r_idx + 1}**")
                    for m_idx, m in enumerate(r):
                        if m["is_bye"]:
                            st.info(f"{m['team1']} (부전승) -> 자동 진출")
                        else:
                            t1 = m["team1"] if m["team1"] else "미정"
                            t2 = m["team2"] if m["team2"] else "미정"
                            if t1 == "미정" and t2 == "미정":
                                st.write("이전 라운드 대기 중...")
                            else:
                                col1, col2, col3, col4 = st.columns([3, 1, 3, 3])
                                with col1:
                                    st.markdown(f"**{t1}**")
                                with col2:
                                    st.markdown("VS")
                                with col3:
                                    st.markdown(f"**{t2}**")
                                with col4:
                                    if t1 != "미정" and t2 != "미정":
                                        winner_opts = ["진행 전", t1, t2]
                                        current_winner = m["winner"] if m["winner"] else "진행 전"
                                        new_winner = st.selectbox("승리팀", winner_opts, index=winner_opts.index(current_winner), key=f"tn_{s['session_id']}_{r_idx}_{m_idx}", label_visibility="collapsed")
                                        if new_winner != current_winner:
                                            actual_winner = None if new_winner == "진행 전" else new_winner
                                            update_tournament_match(s["session_id"], r_idx, m_idx, actual_winner)
                                            st.rerun()
                                    else:
                                        if m["winner"]:
                                            st.success(f"승리: {m['winner']}")
                    st.markdown("---")
            
            st.markdown("#### 🏁 최종 우승팀 확정 및 DB 기록")
            st.markdown("모든 경기가 끝나면 최종 우승팀을 선택하여 대회를 종료하고 이력을 DB에 저장하세요. **(중간 경기는 DB에 남지 않고 최종 우승팀만 반영됩니다)**")
            team_names = [t["name"] for t in s["teams"]]
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                final_winner = st.selectbox("최종 우승팀 선택", ["선택"] + team_names, key=f"final_{s['session_id']}")
            with c_f2:
                if st.button("대회 종료 및 DB 저장", key=f"btn_{s['session_id']}", type="primary"):
                    if final_winner == "선택":
                        st.error("최종 우승팀을 선택해주세요.")
                    else:
                        complete_session(s["session_id"], final_winner)
                        database.add_match("AUCTION", s["host"], final_winner, s["players_data"])
                        st.success("대회가 종료되고 내전 이력에 저장되었습니다!")
                        st.rerun()
    st.divider()
    
st.subheader("종료된 내전 이력")

matches = database.get_matches()

if not matches:
    st.info("아직 진행된 내전 이력이 없습니다.")
else:
    # CSV 다운로드 데이터 준비
    csv_data = []
    for match in matches:
        match_id, match_type, host, match_date, winning_team = match
        type_str = "일반" if match_type == "NORMAL" else "경매"
        players = database.get_match_players(match_id)
        for p in players:
            t_name, role, r_id, t_line, p_score, m_score, p_spent, m_bonus = p
            base_score = m_score if m_score != -1 else p_score
            f_score = base_score + m_bonus
            
            if match_type == "NORMAL" and winning_team and winning_team not in ["아직 모름", ""]:
                effective_tier = calculate_clan_tier(base_score)
                bonus_change = calculate_mmr_delta(effective_tier)
                if t_name == winning_team:
                    change_str = f"+{bonus_change}점"
                else:
                    change_str = f"-{bonus_change}점"
            else:
                change_str = "-"
                
            csv_data.append({
                "매치번호": match_id,
                "내전종류": type_str,
                "날짜": match_date,
                "진행자": host,
                "우승팀": winning_team,
                "소속팀": t_name,
                "역할/포지션": role,
                "닉네임": f"{r_id}#{t_line}",
                "스코어": f_score,
                "파워스코어 증감": change_str
            })
    
    if csv_data:
        df_all = pd.DataFrame(csv_data)
        csv_bytes = df_all.to_csv(index=False).encode('utf-8-sig')
        col1, col2 = st.columns([8, 2])
        with col2:
            st.download_button(
                label="📥 이력 CSV 다운로드",
                data=csv_bytes,
                file_name='match_history.csv',
                mime='text/csv',
            )
            
    for match in matches:
        match_id, match_type, host, match_date, winning_team = match
        
        # Parse date
        date_str = match_date.split(" ")[0]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = dt.strftime("%y년 %m월 %d일")
        except:
            formatted_date = date_str
            
        type_str = "일반" if match_type == "NORMAL" else "경매"
        title = f"[{type_str}] {formatted_date} - 진행자: {host}"
        
        with st.expander(title):
            players = database.get_match_players(match_id)
            # players: mp.team_name, mp.role, u.riot_id, u.tag_line, u.power_score, u.manual_score, mp.points_spent
            
            # Group by team
            teams = {}
            for p in players:
                t_name, role, r_id, t_line, p_score, m_score, p_spent, m_bonus = p
                if t_name not in teams:
                    teams[t_name] = []
                    
                base_score = m_score if m_score != -1 else p_score
                f_score = base_score + m_bonus
                
                if match_type == "NORMAL" and winning_team and winning_team not in ["아직 모름", ""]:
                    effective_tier = calculate_clan_tier(base_score)
                    bonus_change = calculate_mmr_delta(effective_tier)
                    if t_name == winning_team:
                        change_str = f"+{bonus_change}점"
                    else:
                        change_str = f"-{bonus_change}점"
                else:
                    change_str = "-"
                    
                teams[t_name].append({
                    "역할/포지션": role,
                    "닉네임": f"{r_id}#{t_line}",
                    "스코어": f_score,
                    "파워스코어 증감": change_str
                })
                
            team_names = list(teams.keys())
            options = ["아직 모름"] + team_names
            
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                if winning_team and winning_team != "아직 모름":
                    st.markdown(f"### 🏆 승리 팀: {winning_team}")
                else:
                    st.markdown("### 🏆 승리 팀: 미정")
            with c2:
                new_winner = st.selectbox("승리 팀 수정", options, index=options.index(winning_team) if winning_team in options else 0, key=f"sel_{match_id}", label_visibility="collapsed")
            with c3:
                if st.button("저장", key=f"save_{match_id}"):
                    database.update_match_winner(match_id, new_winner)
                    st.rerun()

            if len(teams) > 0:
                cols = st.columns(len(teams))
                for i, (t_name, members) in enumerate(teams.items()):
                    with cols[i]:
                        if t_name == winning_team:
                            st.markdown(f"### 👑 {t_name} (승리)")
                        else:
                            st.markdown(f"### {t_name}")
                            
                        df = pd.DataFrame(members)
                        st.dataframe(df, use_container_width=True)
            else:
                st.warning("이 내전에 등록된 참가자 정보가 없습니다.")
