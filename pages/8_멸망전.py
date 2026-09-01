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

tab1, tab2 = st.tabs(["🏆 멸망전 순위표", "📅 경기 플래너 (매치 등록)"])

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
            "팀명": t,
            "세트 진행": stats[t]["Played"],
            "승": stats[t]["Win"],
            "패": stats[t]["Loss"],
            "승점": stats[t]["Points"],
            "KDA득실차": stats[t]["KDADiff"]
        })
        
    df_leaderboard = pd.DataFrame(df_data)
    st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)
    
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


# ----------------- 탭 2: 경기 플래너 -----------------
with tab2:
    st.subheader("📅 매치 플래너 (9/2 ~ 9/9)")
    st.info("💡 각 매치는 **2세트 연달아 진행**됩니다. 플래너의 방 1개는 1매치(2세트)를 의미합니다.")
    
    dates = ["2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06", "2026-09-07", "2026-09-08", "2026-09-09"]
    selected_date = st.selectbox("날짜 선택", dates)
    
    times = []
    for h in range(24):
        times.append(f"{h:02d}:00")
        times.append(f"{h:02d}:30")
        
    day_schedules = [m for m in schedules if str(m.get("match_date", "")) == selected_date]
    
    cols_per_row = 3
    for row_idx in range(0, len(times), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            if row_idx + col_idx < len(times):
                time_slot = times[row_idx + col_idx]
                matches_in_slot = [m for m in day_schedules if m["time_slot"] == time_slot]
                
                with cols[col_idx]:
                    with st.container(border=True):
                        st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:1.1em; color:#333; margin-bottom:5px;'>⏰ {time_slot}</div>", unsafe_allow_html=True)
                        
                        for idx, match in enumerate(matches_in_slot):
                            is_waiting = (match['team_b'] == "선택" or not match['team_b'])
                            status_color = "#f57c00" if is_waiting else ("#2e7d32" if match["status"] == "COMPLETED" else "#1f77b4")
                            status_text = "상대 대기중" if is_waiting else match["status"]
                            
                            st.markdown(f"<div style='text-align:center; font-size:0.9em; font-weight:bold; color:{status_color}; margin-top:10px;'>{status_text}</div>", unsafe_allow_html=True)
                            
                            if is_waiting:
                                st.markdown(f"<div style='text-align:center; font-size:0.95em;'>{match['team_a']} <br>🆚<br> [?]</div>", unsafe_allow_html=True)
                                with st.expander("🤝 매치 참가"):
                                    with st.form(key=f"join_{match['id']}"):
                                        join_t = st.selectbox("참가 팀 선택", team_names)
                                        if st.form_submit_button("참가하기", type="primary", use_container_width=True):
                                            if join_t == match['team_a']:
                                                st.error("같은 팀은 참가할 수 없습니다.")
                                            else:
                                                all_schedules = database.get_deathmatch_schedules()
                                                join_total = sum(1 for s in all_schedules if s['team_a']==join_t or s['team_b']==join_t)
                                                h2h_count = sum(1 for s in all_schedules if (s['team_a']==match['team_a'] and s['team_b']==join_t) or (s['team_a']==join_t and s['team_b']==match['team_a']))
                                                time_conflict = any(s['match_date']==selected_date and s['time_slot']==time_slot and (s['team_a']==join_t or s['team_b']==join_t) for s in all_schedules)
                                                
                                                if join_total >= 8:
                                                    st.error(f"{join_t}은(는) 이미 최대 매치(8회)를 모두 채웠습니다.")
                                                elif h2h_count >= 1:
                                                    st.error("두 팀 간의 매치는 이미 등록되어 있습니다 (최대 1회 제한).")
                                                elif time_conflict:
                                                    st.error(f"{join_t}은(는) 이 시간에 이미 다른 매치에 참가 중입니다.")
                                                else:
                                                    if database.join_deathmatch_schedule(match['id'], join_t):
                                                        st.success("매치에 참가했습니다!")
                                                        st.rerun()
                                        if st.form_submit_button("❌ 방 삭제", use_container_width=True):
                                            if database.delete_deathmatch_schedule(match['id']):
                                                st.success("매치가 삭제되었습니다.")
                                                st.rerun()
                            else:
                                st.markdown(f"<div style='text-align:center; font-size:0.95em;'>{match['team_a']} <br>🆚<br> {match['team_b']}</div>", unsafe_allow_html=True)
                                
                                if match["status"] == "SCHEDULED":
                                    with st.expander("📝 2세트 결과 입력"):
                                        with st.form(key=f"form_result_{match['id']}"):
                                            st.markdown("**1세트 결과**")
                                            w1 = st.selectbox("1세트 승리", [match['team_a'], match['team_b']], key=f"w1_{match['id']}")
                                            col_1a, col_1b = st.columns(2)
                                            with col_1a:
                                                ka1 = st.number_input(f"{match['team_a']} 킬 (1세트)", min_value=0, max_value=200, step=1, key=f"ka1_{match['id']}")
                                            with col_1b:
                                                kb1 = st.number_input(f"{match['team_b']} 킬 (1세트)", min_value=0, max_value=200, step=1, key=f"kb1_{match['id']}")
                                                
                                            st.markdown("---")
                                            st.markdown("**2세트 결과**")
                                            w2 = st.selectbox("2세트 승리", [match['team_a'], match['team_b']], key=f"w2_{match['id']}")
                                            col_2a, col_2b = st.columns(2)
                                            with col_2a:
                                                ka2 = st.number_input(f"{match['team_a']} 킬 (2세트)", min_value=0, max_value=200, step=1, key=f"ka2_{match['id']}")
                                            with col_2b:
                                                kb2 = st.number_input(f"{match['team_b']} 킬 (2세트)", min_value=0, max_value=200, step=1, key=f"kb2_{match['id']}")
                                            
                                            st.markdown("---")
                                            is_forfeit = st.checkbox("🚩 매치 전체 기권 (양팀 모두 패배, KDA 득실차 총 -10 반영)", key=f"ff_{match['id']}")
                                            
                                            if st.form_submit_button("결과 저장", type="primary", use_container_width=True):
                                                if database.update_deathmatch_result(match['id'], w1, ka1, kb1, w2, ka2, kb2, is_forfeit):
                                                    st.success("결과가 저장되었습니다.")
                                                    st.rerun()
                                            
                                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                                            if st.form_submit_button("❌ 매치 취소 (삭제)", use_container_width=True):
                                                if database.delete_deathmatch_schedule(match['id']):
                                                    st.success("매치가 취소되었습니다.")
                                                    st.rerun()
                                elif match["status"] == "COMPLETED":
                                    if str(match.get("is_forfeit", "FALSE")).upper() == "TRUE":
                                        st.markdown("<div style='text-align:center; font-size:0.8em; color:red; margin-bottom:10px;'>🚩 전체 기권패 처리됨</div>", unsafe_allow_html=True)
                                    else:
                                        # 1세트
                                        st.markdown(f"<div style='text-align:center; font-size:0.8em; color:#444; background:#f0f0f0; margin:2px; border-radius:4px;'><b>1세트 승리: {match.get('winner1','?')}</b> ({match.get('team_a_kills1','?')} vs {match.get('team_b_kills1','?')})</div>", unsafe_allow_html=True)
                                        # 2세트
                                        st.markdown(f"<div style='text-align:center; font-size:0.8em; color:#444; background:#f0f0f0; margin:2px; border-radius:4px;'><b>2세트 승리: {match.get('winner2','?')}</b> ({match.get('team_a_kills2','?')} vs {match.get('team_b_kills2','?')})</div>", unsafe_allow_html=True)
                                        
                                    with st.expander("🔄 결과 수정"):
                                        st.markdown("<div style='font-size:0.85em; color:#666; margin-bottom:10px;'>결과를 수정하려면 먼저 저장된 결과를 리셋해야 합니다.</div>", unsafe_allow_html=True)
                                        if st.button("결과 초기화 (저장 해제)", key=f"reset_{match['id']}", use_container_width=True):
                                            if database.reset_deathmatch_result(match['id']):
                                                st.success("결과가 초기화되었습니다. 다시 입력해주세요.")
                                                st.rerun()
                                        
                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                                        
                        # Add new match button for this slot
                        with st.expander("➕ 새 방 파기 (1매치=2세트)"):
                            with st.form(key=f"form_reg_{time_slot}"):
                                t_a = st.selectbox("방장 팀", team_names, key=f"ta_{time_slot}")
                                t_b_options = ["선택"] + team_names
                                t_b = st.selectbox("상대 팀 (비워두면 대기)", t_b_options, key=f"tb_{time_slot}")
                                
                                if st.form_submit_button("방 만들기", type="primary", use_container_width=True):
                                    if t_b != "선택" and t_a == t_b:
                                        st.error("서로 다른 팀을 선택해주세요.")
                                    else:
                                        all_schedules = database.get_deathmatch_schedules()
                                        
                                        # 최대 매치수 8 (16게임) 검증
                                        a_total = sum(1 for s in all_schedules if s['team_a']==t_a or s['team_b']==t_a)
                                        b_total = sum(1 for s in all_schedules if s['team_a']==t_b or s['team_b']==t_b)
                                        
                                        # 맞대결 1회 제한 검증
                                        h2h_count = sum(1 for s in all_schedules if (s['team_a']==t_a and s['team_b']==t_b) or (s['team_a']==t_b and s['team_b']==t_a)) if t_b != "선택" else 0
                                        
                                        # 동시간대 같은 팀 참가 방지 (선택 옵션)
                                        time_conflict_a = any(s['match_date']==selected_date and s['time_slot']==time_slot and (s['team_a']==t_a or s['team_b']==t_a) for s in all_schedules)
                                        time_conflict_b = any(s['match_date']==selected_date and s['time_slot']==time_slot and (s['team_a']==t_b or s['team_b']==t_b) for s in all_schedules) if t_b != "선택" else False

                                        if a_total >= 8:
                                            st.error(f"{t_a}은(는) 이미 최대 매치(8회)를 모두 채웠습니다.")
                                        elif t_b != "선택" and b_total >= 8:
                                            st.error(f"{t_b}은(는) 이미 최대 매치(8회)를 모두 채웠습니다.")
                                        elif h2h_count >= 1:
                                            st.error("두 팀 간의 매치는 이미 등록되어 있습니다 (최대 1회 제한).")
                                        elif time_conflict_a:
                                            st.error(f"{t_a}은(는) 이 시간에 이미 다른 매치에 참가 중입니다.")
                                        elif time_conflict_b:
                                            st.error(f"{t_b}은(는) 이 시간에 이미 다른 매치에 참가 중입니다.")
                                        else:
                                            if database.add_deathmatch_schedule(selected_date, time_slot, t_a, t_b):
                                                st.toast("✅ 방이 성공적으로 생성되었습니다!")
                                                st.rerun()
