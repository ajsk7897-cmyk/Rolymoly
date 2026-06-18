import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
import importlib
importlib.reload(database)

st.set_page_config(page_title="내전 이력", page_icon="📜", layout="wide")

st.title("📜 내전 이력")

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
            t_name, role, r_id, t_line, p_score, m_score, p_spent = p
            f_score = m_score if m_score != -1 else p_score
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
                "소모포인트": p_spent if match_type == "AUCTION" else "-"
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
                t_name, role, r_id, t_line, p_score, m_score, p_spent = p
                if t_name not in teams:
                    teams[t_name] = []
                f_score = m_score if m_score != -1 else p_score
                teams[t_name].append({
                    "역할/포지션": role,
                    "닉네임": f"{r_id}#{t_line}",
                    "스코어": f_score,
                    "소모포인트": p_spent if match_type == "AUCTION" else "-"
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

            cols = st.columns(len(teams))
            for i, (t_name, members) in enumerate(teams.items()):
                with cols[i]:
                    if t_name == winning_team:
                        st.markdown(f"### 👑 {t_name} (승리)")
                    else:
                        st.markdown(f"### {t_name}")
                        
                    df = pd.DataFrame(members)
                    st.dataframe(df, use_container_width=True)
