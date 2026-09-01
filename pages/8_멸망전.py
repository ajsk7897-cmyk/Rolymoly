import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

st.set_page_config(page_title="멸망전 (Deathmatch)", page_icon="⚔️", layout="wide")

st.markdown("""
<style>
div[data-testid="stToast"] {
    font-size: 1.1rem !important;
    background-color: #e6ffe6 !important;
}
/* 매트릭스 표 중앙 정렬 */
.dataframe th, .dataframe td {
    text-align: center !important;
}
</style>
""", unsafe_allow_html=True)

st.title("⚔️ 클랜 멸망전 (Deathmatch)")

# Data Loading
teams_data = database.get_deathmatch_teams()
team_names = list(teams_data.keys())
schedules = database.get_deathmatch_schedules()

tab1, tab2 = st.tabs(["🏆 멸망전 순위표", "📝 매치 결과 등록"])

# ----------------- 탭 1: 순위표 -----------------
with tab1:
    st.subheader("📊 풀리그 순위표 (2세트 합산)")
    
    # 통계 딕셔너리 초기화
    stats = {t: {"Played": 0, "Win": 0, "Loss": 0, "Points": 0, "KDADiff": 0} for t in team_names}
    
    # 승자승 기록용 매트릭스 [Team A][Team B] = 승리횟수 (단위: 세트)
    h2h_wins = {t: {opp: 0 for opp in team_names} for t in team_names}
    
    completed_matches = [m for m in schedules if m.get("status") == "COMPLETED"]
    
    for m in completed_matches:
        t_a = m["team_a"]
        t_b = m["team_b"]
        
        if t_a not in stats or t_b not in stats:
            continue
            
        stats[t_a]["Played"] += 2  # 1매치 = 2세트
        stats[t_b]["Played"] += 2
        
        if str(m.get("is_forfeit", "FALSE")).upper() == "TRUE":
            # 기권의 경우 양팀 2패 누적, 득실차는 총 -10 적용
            stats[t_a]["Loss"] += 2
            stats[t_b]["Loss"] += 2
            stats[t_a]["KDADiff"] -= 10
            stats[t_b]["KDADiff"] -= 10
        else:
            w1 = str(m.get("winner1", ""))
            ka1 = int(m.get("team_a_kills1", 0))
            kb1 = int(m.get("team_b_kills1", 0))
            
            w2 = str(m.get("winner2", ""))
            ka2 = int(m.get("team_a_kills2", 0))
            kb2 = int(m.get("team_b_kills2", 0))
            
            # 세트 1 계산
            if w1 == t_a:
                stats[t_a]["Win"] += 1
                stats[t_a]["Points"] += 3
                stats[t_b]["Loss"] += 1
                h2h_wins[t_a][t_b] += 1
            elif w1 == t_b:
                stats[t_b]["Win"] += 1
                stats[t_b]["Points"] += 3
                stats[t_a]["Loss"] += 1
                h2h_wins[t_b][t_a] += 1
            
            # 세트 2 계산
            if w2 == t_a:
                stats[t_a]["Win"] += 1
                stats[t_a]["Points"] += 3
                stats[t_b]["Loss"] += 1
                h2h_wins[t_a][t_b] += 1
            elif w2 == t_b:
                stats[t_b]["Win"] += 1
                stats[t_b]["Points"] += 3
                stats[t_a]["Loss"] += 1
                h2h_wins[t_b][t_a] += 1
                
            # 득실차 반영
            diff_a = (ka1 - kb1) + (ka2 - kb2)
            diff_b = (kb1 - ka1) + (kb2 - ka2)
            stats[t_a]["KDADiff"] += diff_a
            stats[t_b]["KDADiff"] += diff_b
                
    # 순위 정렬
    def tiebreaker_sort_key(t):
        return (stats[t]["Points"], stats[t]["KDADiff"])
        
    sorted_teams = sorted(team_names, key=tiebreaker_sort_key, reverse=True)
    
    # 승자승 보정 (Points와 KDADiff가 같을 때만)
    for i in range(len(sorted_teams)):
        for j in range(i+1, len(sorted_teams)):
            t1 = sorted_teams[i]
            t2 = sorted_teams[j]
            if stats[t1]["Points"] == stats[t2]["Points"] and stats[t1]["KDADiff"] == stats[t2]["KDADiff"]:
                if h2h_wins[t2][t1] > h2h_wins[t1][t2]:
                    sorted_teams[i], sorted_teams[j] = sorted_teams[j], sorted_teams[i]
    
    df_data = []
    for idx, t in enumerate(sorted_teams):
        df_data.append({
            "순위": idx + 1,
            "승점": stats[t]["Points"],
            "팀명": t,
            "세트 진행": stats[t]["Played"],
            "승": stats[t]["Win"],
            "패": stats[t]["Loss"],
            "KDA득실차": stats[t]["KDADiff"]
        })
        
    df_leaderboard = pd.DataFrame(df_data)
    
    def highlight_points(s):
        return ['background-color: #e6ffe6' if s.name == '승점' else '' for _ in s]
        
    styled_df = df_leaderboard.style.apply(highlight_points)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("⚔️ 승패 매트릭스 (Head-to-head 세트 승패)")
    matrix_data = []
    for t_row in team_names:
        row_dict = {"팀명": t_row}
        for t_col in team_names:
            if t_row == t_col:
                row_dict[t_col] = "-"
            else:
                wins = h2h_wins[t_row][t_col]
                losses = h2h_wins[t_col][t_row]
                if wins == 0 and losses == 0:
                    row_dict[t_col] = " "
                else:
                    row_dict[t_col] = f"{wins}승 {losses}패"
        matrix_data.append(row_dict)
        
    df_matrix = pd.DataFrame(matrix_data)
    st.dataframe(df_matrix, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛡️ 참가 팀 로스터")
    
    cols = st.columns(3)
    for idx, t_name in enumerate(team_names):
        roster = teams_data[t_name]
        with cols[idx % 3]:
            st.markdown(f"""
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <h4 style="margin-top: 0; color: #1f77b4; text-align: center;">{t_name}</h4>
                <hr style="margin: 10px 0;">
                <div style="display: grid; grid-template-columns: 40px 1fr; gap: 5px; font-size: 0.95em;">
                    <div style="font-weight: bold; color: #555;">TOP</div><div>{roster['TOP']} {'👑' if roster['Leader']=='TOP' else ''}</div>
                    <div style="font-weight: bold; color: #555;">JG</div><div>{roster['JG']} {'👑' if roster['Leader']=='JG' else ''}</div>
                    <div style="font-weight: bold; color: #555;">MID</div><div>{roster['MID']} {'👑' if roster['Leader']=='MID' else ''}</div>
                    <div style="font-weight: bold; color: #555;">AD</div><div>{roster['AD']} {'👑' if roster['Leader']=='AD' else ''}</div>
                    <div style="font-weight: bold; color: #555;">SUP</div><div>{roster['SUP']} {'👑' if roster['Leader']=='SUP' else ''}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ----------------- 탭 2: 매치 결과 등록 -----------------
with tab2:
    st.subheader("📝 멸망전 결과 직접 등록")
    st.info("💡 팀 간의 2세트 경기 결과를 한 번에 등록합니다. 한 팀당 전체 대회 기간 중 최대 8번의 매치(16세트)만 가능하며, 동일한 두 팀 간의 매치는 단 1회만 등록 가능합니다.")
    
    with st.expander("➕ 새 매치 결과 등록", expanded=True):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_a = st.selectbox("Team A", team_names, key="reg_ta")
        with col_t2:
            t_b = st.selectbox("Team B", team_names, key="reg_tb")
            
        with st.form(key="form_register_match"):
            st.markdown("##### 1세트 결과")
            w1 = st.selectbox("1세트 승리팀", [t_a, t_b], key="reg_w1")
            col_k1a, col_k1b = st.columns(2)
            with col_k1a:
                ka1 = st.number_input(f"{t_a} 킬 (1세트)", min_value=0, max_value=200, step=1, key="reg_ka1")
            with col_k1b:
                kb1 = st.number_input(f"{t_b} 킬 (1세트)", min_value=0, max_value=200, step=1, key="reg_kb1")
                
            st.markdown("---")
            st.markdown("##### 2세트 결과")
            w2 = st.selectbox("2세트 승리팀", [t_a, t_b], key="reg_w2")
            col_k2a, col_k2b = st.columns(2)
            with col_k2a:
                ka2 = st.number_input(f"{t_a} 킬 (2세트)", min_value=0, max_value=200, step=1, key="reg_ka2")
            with col_k2b:
                kb2 = st.number_input(f"{t_b} 킬 (2세트)", min_value=0, max_value=200, step=1, key="reg_kb2")
                
            st.markdown("---")
            is_forfeit = st.checkbox("🚩 매치 전체 기권 (양팀 모두 2패, KDA 득실차 총 -10 반영)", key="reg_ff")
            
            if st.form_submit_button("✅ 결과 등록하기", type="primary", use_container_width=True):
                if t_a == t_b:
                    st.error("서로 다른 팀을 선택해주세요.")
                else:
                    all_schedules = database.get_deathmatch_schedules()
                    completed = [s for s in all_schedules if s['status'] == "COMPLETED"]
                    
                    # 최대 매치 검증
                    a_total = sum(1 for s in completed if s['team_a']==t_a or s['team_b']==t_a)
                    b_total = sum(1 for s in completed if s['team_a']==t_b or s['team_b']==t_b)
                    
                    # 맞대결 검증
                    h2h_count = sum(1 for s in completed if (s['team_a']==t_a and s['team_b']==t_b) or (s['team_a']==t_b and s['team_b']==t_a))
                    
                    if a_total >= 8:
                        st.error(f"{t_a}은(는) 이미 최대 매치(8회)를 모두 채웠습니다.")
                    elif b_total >= 8:
                        st.error(f"{t_b}은(는) 이미 최대 매치(8회)를 모두 채웠습니다.")
                    elif h2h_count >= 1:
                        st.error("두 팀 간의 매치는 이미 등록되어 있습니다 (최대 1회 제한).")
                    else:
                        if database.register_deathmatch_result(t_a, t_b, w1, ka1, kb1, w2, ka2, kb2, is_forfeit):
                            st.success("결과가 성공적으로 등록되었습니다!")
                            st.rerun()

    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    st.subheader("📚 등록된 매치 히스토리")
    
    completed_matches = [m for m in schedules if m.get("status") == "COMPLETED"]
    if not completed_matches:
        st.info("아직 등록된 경기 결과가 없습니다.")
    else:
        # 역순 출력 (최근 등록 순)
        for match in reversed(completed_matches):
            with st.container(border=True):
                st.markdown(f"#### {match['team_a']} 🆚 {match['team_b']}")
                
                if str(match.get("is_forfeit", "FALSE")).upper() == "TRUE":
                    st.markdown("<div style='color:red;'><b>🚩 기권패 처리됨</b> (양팀 모두 KDA -10)</div>", unsafe_allow_html=True)
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**1세트 승리:** {match.get('winner1','?')} ({match.get('team_a_kills1','?')} vs {match.get('team_b_kills1','?')})")
                    with col2:
                        st.markdown(f"**2세트 승리:** {match.get('winner2','?')} ({match.get('team_a_kills2','?')} vs {match.get('team_b_kills2','?')})")
                
                if st.button("❌ 이 매치 기록 삭제", key=f"del_{match['id']}"):
                    if database.delete_deathmatch_schedule(match['id']):
                        st.success("매치 기록이 삭제되었습니다.")
                        st.rerun()
