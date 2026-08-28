import streamlit as st
import sys
import os
import random
import time
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from utils.helpers import format_user_for_selectbox, calculate_auction_points
from utils.tournament_manager import create_session
from utils.auction_state import load_auction_state, save_auction_state, clear_auction_state, update_bid, update_pass

from config import MIN_PLAYERS_REQUIRED, AUCTION_TEAM_OPTIONS

st.set_page_config(page_title="경매 내전", page_icon="💰", layout="wide")

# CSS
st.markdown("""
<style>
div[data-testid="stToast"] { font-size: 1.1rem !important; background-color: #e6ffe6 !important; white-space: nowrap !important; }
[data-testid="stExpander"] details summary { display: flex !important; align-items: center !important; }
[data-testid="stExpander"] details summary > * { flex: 1 !important; text-align: center !important; display: flex !important; justify-content: center !important; }
[data-testid="stExpander"] details summary svg { flex: 0 !important; }
[data-testid="stExpander"] details summary p { width: 100% !important; text-align: center !important; font-weight: bold !important; display: inline-block !important; }
[data-testid="stButton"] p { white-space: pre-wrap !important; }
</style>
""", unsafe_allow_html=True)

st.title("💰 경매 내전")

approved_users = database.get_all_approved_users()
auction_points, _ = database.get_auction_points_by_user()

if not approved_users or len(approved_users) < MIN_PLAYERS_REQUIRED:
    st.warning(f"승인된 회원이 {MIN_PLAYERS_REQUIRED}명 이상이어야 경매 내전을 진행할 수 있습니다.")
    st.stop()

@st.cache_data(ttl=60)
def get_formatted_users_for_auction(users):
    options = [format_user_for_selectbox(u) for u in users]
    u_dict = {u[1]: u for u in options}
    return options, u_dict

user_options, user_dict = get_formatted_users_for_auction(approved_users)

@st.fragment
def team_leader_bid_fragment(my_team_id, my_team_points):
    latest_state = load_auction_state()
    latest_bids = latest_state.get('current_bids', {})
    my_bid_info = latest_bids.get(str(my_team_id))

    if my_bid_info and my_bid_info['status'] == 'BID':
        st.success(f"✅ 현재 {my_bid_info['amount']}p 제출 완료! (남은 시간 동안 재입찰 가능)")
    elif my_bid_info and my_bid_info['status'] == 'PASS':
        st.warning("❌ 미입찰(Pass) 상태입니다. (남은 시간 동안 다시 입찰 가능)")

    st.markdown("---")
    
    current_val = my_bid_info['amount'] if my_bid_info and my_bid_info['status'] == 'BID' else 0
    current_val = min(current_val, my_team_points)
    
    with st.form(key=f"bid_form_{my_team_id}", border=False):
        bid_val = st.number_input("입찰 포인트", min_value=0, max_value=my_team_points, value=current_val, step=10, key=f"bid_input_{my_team_id}")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            submit_bid = st.form_submit_button("입찰하기 / 금액수정", type="primary", use_container_width=True)
        with col_b2:
            submit_pass = st.form_submit_button("해당 턴 미입찰 (Pass)", use_container_width=True)
        
        if submit_bid:
            update_bid(my_team_id, bid_val)
            st.rerun(scope="fragment")
        if submit_pass:
            update_pass(my_team_id)
            st.rerun(scope="fragment")

state = load_auction_state()

# ----------------- 1. 역할 선택 (Role Selection) -----------------
if state:
    st.info("🚨 현재 진행 중인 실시간 경매가 있습니다. 본인의 역할을 선택해주세요.")
    
    # Extract roles available
    role_options = ["관전 (일반 회원)"]
    host_name = state.get("host_name", "진행자")
    
    role_options.append(f"진행자 ({host_name})")
    
    # Team leaders
    team_leader_map = {}
    for team in state["teams"]:
        if team["members"]:
            leader = team["members"][0]
            leader_name = user_dict[leader["user_id"]][0].split('#')[0] if leader["user_id"] in user_dict else "Leader"
            role_name = f"팀장 ({team['name']} - {leader_name})"
            role_options.append(role_name)
            team_leader_map[role_name] = team["id"]
        
    my_role = st.selectbox("👤 접속자 본인의 역할을 선택해주세요", role_options, key="my_role_selection")
    
    is_host = my_role.startswith("진행자")
    is_team_leader = my_role.startswith("팀장")
    my_team_id = team_leader_map.get(my_role) if is_team_leader else None
else:
    is_host = True
    is_team_leader = False
    my_team_id = None

# ----------------- 2. 경매 세팅 (Setup) -----------------
if not state:
    st.subheader("1. 경매 내전 설정")
    host_mode = st.radio("진행자 입력 방식", ["회원 선택", "직접 입력"], horizontal=True)
    if host_mode == "회원 선택":
        host_id = st.selectbox("진행자 (회원)", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0].split('#')[0] if x else "선택 없음", index=None, placeholder="참가자 입력")
        host_name = user_dict[host_id][0].split('#')[0] if host_id else None
    else:
        host_id = "CUSTOM_HOST"
        host_name = st.text_input("진행자 (직접 입력)")

    st.markdown("#### 👤 경매 전체 참가자 선택 (팀장 포함)")
    selected_participants = st.multiselect("이번 경매에 참가할 전체 선수들을 선택해주세요.", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0])

    num_teams_input = st.selectbox("팀 구성 수", [4, 6, 8])

    with st.form("auction_setup"):
        leaders = []
        cols = st.columns(3, vertical_alignment="bottom")
        for i in range(num_teams_input):
            with cols[i % 3]:
                leader = st.selectbox(f"Team {i+1} 팀장", options=[None] + selected_participants, format_func=lambda x: "선택안함" if x is None else user_dict[x][0], index=None)
                leaders.append(leader)
        
        start_btn = st.form_submit_button("실시간 경매 시작")
        if start_btn:
            if not selected_participants:
                st.error("참가자를 1명 이상 선택해주세요.")
            elif not host_name:
                st.error("진행자를 지정해주세요.")
            else:
                actual_leaders = [l for l in leaders if l is not None]
                if len(set(actual_leaders)) != len(actual_leaders):
                    st.error("중복된 팀장이 있습니다.")
                else:
                    teams = []
                    for i in range(num_teams_input):
                        leader_id = leaders[i]
                        if leader_id:
                            leader_info = user_dict[leader_id]
                            team_points = calculate_auction_points(leader_info[2])
                            teams.append({'id': i, 'name': f"{leader_info[0].split('#')[0]} 팀", 'points': team_points, 'members': [{'user_id': leader_id, 'points_spent': 0, 'role': 'Leader'}]})
                        else:
                            teams.append({'id': i, 'name': f"Team {i+1}", 'points': 1000, 'members': []})
                    
                    new_state = {
                        "auction_started": True,
                        "host_id": host_id,
                        "host_name": host_name,
                        "num_teams": num_teams_input,
                        "teams": teams,
                        "remaining_pool": [p for p in selected_participants if p not in actual_leaders],
                        "skipped_pool": [],
                        "current_target": None,
                        "auction_phase": "WAITING",
                        "bid_end_time": 0,
                        "current_bids": {}
                    }
                    save_auction_state(new_state)
                    st.rerun()

# ----------------- 3. 실시간 경매 진행 UI -----------------
if state:
    @st.fragment(run_every="1s")
    def live_auction_board():
        current_state = load_auction_state()
        if not current_state:
            st.warning("경매가 종료되었거나 초기화되었습니다. 새로고침을 눌러주세요.")
            return

        phase = current_state.get('auction_phase')
        teams = current_state.get('teams')
        current_target = current_state.get('current_target')
        bids = current_state.get('current_bids', {})
        
        st.subheader(f"📡 실시간 경매 진행 중 (진행자: {current_state['host_name']})")
        
        # Team Display Logic
        cols_per_row = 3 if current_state['num_teams'] == 6 else 4
        for row_start in range(0, current_state['num_teams'], cols_per_row):
            cols = st.columns(cols_per_row, vertical_alignment="top")
            for col_idx in range(cols_per_row):
                if row_start + col_idx < current_state['num_teams']:
                    team = teams[row_start + col_idx]
                    with cols[col_idx]:
                        html = f"""
                        <div style="background-color: #d1d6df; border-radius: 8px; padding: 6px; border: 1px solid #a3aab5; min-height: 110px; margin-bottom: 10px;">
                            <div style="font-size: 0.95rem; font-weight: bold; text-align: center; color: #000; margin-bottom: 2px;">{team['name']}</div>
                            <div style="font-size: 0.9rem; font-weight: bold; text-align: center; color: #d32f2f; margin-bottom: 4px;">잔여 P: {team['points']}</div>
                            <hr style="margin: 2px 0 4px 0; border: 0; border-top: 2px solid #999;">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; padding: 2px 0;">
                        """
                        for m in team['members']:
                            if m['role'] == 'Leader': continue
                            raw_name = user_dict[m['user_id']][0].split(' (')[0].split('#')[0]
                            if '] ' in raw_name: raw_name = raw_name.split('] ')[-1]
                            html += f"<div style='font-size: 0.75rem; color: #000; overflow: hidden; text-overflow: ellipsis;'>- {raw_name} ({m['points_spent']})</div>"
                        html += "</div></div>"
                        st.markdown(html, unsafe_allow_html=True)
                        
        st.markdown("<hr>", unsafe_allow_html=True)

        # Main Auction Area
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🎯 현재 대상")
            st.write(f"남은 인원: {len(current_state['remaining_pool'])}명 / 유찰: {len(current_state['skipped_pool'])}명")
            
            if is_host and phase == "WAITING":
                if st.button("🎲 다음 참가자 뽑기", type="primary"):
                    if current_state['remaining_pool']:
                        target = random.choice(current_state['remaining_pool'])
                        current_state['current_target'] = target
                        current_state['auction_phase'] = "WAITING"
                        current_state['current_bids'] = {}
                        save_auction_state(current_state)
                        st.rerun()
                    else:
                        st.warning("남은 참가자가 없습니다.")
                        
                if not current_state['remaining_pool'] and current_state['skipped_pool']:
                    if st.button("🔄 유찰자 재경매 (남은 인원으로 복구)"):
                        current_state['remaining_pool'] = current_state['skipped_pool']
                        current_state['skipped_pool'] = []
                        save_auction_state(current_state)
                        st.rerun()
                        
            if current_target:
                t_user = user_dict[current_target]
                st.markdown(f"""
                <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4;">
                    <span style="font-size: 1.2em; font-weight: bold; color: #000;">{t_user[0]}</span><br>
                    <b>🏆 클랜 티어:</b> {t_user[3]} | <b>⚔️ 포지션:</b> 주 <b>{t_user[4]}</b> 부 <b>{t_user[5]}</b>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("### 📝 입찰 현황 (블라인드)")
            if not current_target:
                st.info("진행자가 대상을 뽑기를 기다려주세요.")
            elif phase == "WAITING":
                if is_host:
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        timer_input = st.selectbox("최초 타이머 설정 (초)", [0, 3, 5, 7, 10, 15, 20], format_func=lambda x: "제한 없음" if x == 0 else f"{x}초")
                    with col_t2:
                        extend_input = st.selectbox("상위 입찰 시 연장 (초)", [0, 3, 5, 7, 10], format_func=lambda x: "사용 안 함" if x == 0 else f"{x}초 연장")
                    
                    col_w1, col_w2 = st.columns(2)
                    with col_w1:
                        if st.button("▶️ 호가 접수 시작", type="primary", use_container_width=True):
                            current_state['auction_phase'] = "BIDDING"
                            current_state['bid_end_time'] = (time.time() + timer_input) if timer_input > 0 else 0
                            current_state['extend_time'] = extend_input
                            save_auction_state(current_state)
                            st.rerun()
                    with col_w2:
                        if st.button("⏭️ 즉시 유찰", use_container_width=True):
                            current_state['remaining_pool'].remove(current_target)
                            current_state['skipped_pool'].append(current_target)
                            current_state['current_target'] = None
                            save_auction_state(current_state)
                            st.rerun()
                else:
                    st.info("진행자가 경매 시작을 준비중입니다...")
                    
            elif phase == "BIDDING":
                if current_state.get('bid_end_time', 0) > 0:
                    rem_time = max(0, int(current_state['bid_end_time'] - time.time()))
                    st.markdown(f"#### ⏳ 남은 시간: <span style='color:red;'>{rem_time}초</span>", unsafe_allow_html=True)
                    
                    # Auto resolve when time is up
                    if rem_time == 0 and is_host:
                        current_state['auction_phase'] = "RESOLVED"
                        save_auction_state(current_state)
                        st.rerun()
                else:
                    st.markdown("#### ⏳ 남은 시간: <span style='color:blue;'>제한 없음 (수동 조기 마감)</span>", unsafe_allow_html=True)

                # Status of bids (Open Racing Graph)
                valid_bids = [b['amount'] for b in bids.values() if b['status'] == 'BID']
                max_bid = max(valid_bids) if valid_bids else 0
                scale_max = max(300, max_bid * 1.2) # Max scale is at least 300p, or 120% of max bid

                html_bars = ""
                for t in teams:
                    b = bids.get(str(t['id']))
                    amt = b['amount'] if b and b['status'] == 'BID' else 0
                    is_pass = b and b['status'] == 'PASS'
                    
                    pct = min(100, int((amt / scale_max) * 100))
                    
                    if amt > 0 and amt == max_bid:
                        color = "linear-gradient(90deg, #FFD700 0%, #FF8C00 100%)" # Gold gradient
                        text_color = "#000"
                        medal = "👑"
                        text_shadow = "none"
                    else:
                        color = "#1f77b4" # Blue
                        text_color = "#fff"
                        medal = ""
                        text_shadow = "1px 1px 2px rgba(0,0,0,0.5)"
                        
                    if is_pass:
                        bar_html = f'''<div style="color: #999; font-weight: bold; margin-bottom: 8px;">{t['name']}: 미입찰 (Pass)</div>'''
                    else:
                        display_text = f"{t['name']}: {amt}p {medal}" if amt > 0 else f"{t['name']}: 0p (고민 중🤔)"
                        font_col = "#000" if amt == 0 else text_color
                        shadow = "none" if amt == 0 else text_shadow
                        bar_html = f'''
                        <div style="margin-bottom: 8px;">
                            <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; height: 28px; position: relative;">
                                <div style="width: {pct}%; background: {color}; height: 100%; border-radius: 5px; transition: width 0.3s ease-in-out;"></div>
                                <div style="position: absolute; top: 0; left: 10px; line-height: 28px; font-weight: 800; font-size: 14.5px; color: {font_col}; text-shadow: {shadow}; white-space: nowrap;">
                                    {display_text}
                                </div>
                            </div>
                        </div>
                        '''
                    html_bars += bar_html
                st.markdown(html_bars, unsafe_allow_html=True)
                
                if is_team_leader:
                    my_team_points = next(t['points'] for t in teams if t['id'] == my_team_id)
                    team_leader_bid_fragment(my_team_id, my_team_points)

                if is_host:
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        if st.button("조기 마감 (결과 보기)", use_container_width=True):
                            current_state['auction_phase'] = "RESOLVED"
                            save_auction_state(current_state)
                            st.rerun()
                    with col_h2:
                        if st.button("🔄 재입찰 (타이머 다시 시작)", use_container_width=True):
                            current_state['auction_phase'] = "WAITING"
                            current_state['current_bids'] = {}
                            save_auction_state(current_state)
                            st.rerun()
                    
            elif phase == "RESOLVED":
                st.markdown("#### 🎉 입찰 결과 공개")
                
                valid_bids = []
                for t in teams:
                    bid_info = bids.get(str(t['id']))
                    if bid_info and bid_info['status'] == 'BID':
                        valid_bids.append((t['id'], t['name'], bid_info['amount'], bid_info['time']))
                    elif bid_info and bid_info['status'] == 'PASS':
                        st.write(f"- {t['name']}: 미입찰")
                        
                valid_bids.sort(key=lambda x: (-x[2], x[3]))
                
                if not valid_bids:
                    st.warning("입찰한 팀이 없습니다.")
                else:
                    for idx, (t_id, t_name, amt, _) in enumerate(valid_bids):
                        if idx == 0:
                            st.markdown(f"**👑 1위: {t_name} ({amt}p)**")
                        else:
                            st.write(f"{idx+1}위: {t_name} ({amt}p)")
                            
                if is_host:
                    st.markdown("---")
                    st.write("진행자: 최종 낙찰할 팀을 선택하세요")
                    cols_h = st.columns(min(len(valid_bids), 4) if valid_bids else 1)
                    
                    if valid_bids:
                        for idx, (t_id, t_name, amt, _) in enumerate(valid_bids):
                            with cols_h[idx % len(cols_h)]:
                                if st.button(f"{t_name} 낙찰\n({amt}p)", key=f"win_{t_id}", type="primary"):
                                    for t in current_state['teams']:
                                        if t['id'] == t_id:
                                            t['points'] -= amt
                                            t['members'].append({'user_id': current_target, 'points_spent': amt, 'role': 'Member'})
                                    current_state['remaining_pool'].remove(current_target)
                                    current_state['current_target'] = None
                                    current_state['auction_phase'] = "WAITING"
                                    current_state['current_bids'] = {}
                                    save_auction_state(current_state)
                                    st.rerun()
                    
                    if st.button("⏭️ 최종 유찰 (아무도 낙찰받지 않음)"):
                        current_state['remaining_pool'].remove(current_target)
                        current_state['skipped_pool'].append(current_target)
                        current_state['current_target'] = None
                        current_state['auction_phase'] = "WAITING"
                        current_state['current_bids'] = {}
                        save_auction_state(current_state)
                        st.rerun()
                        
                    if st.button("🔄 재입찰 (타이머 다시 시작)"):
                        current_state['auction_phase'] = "WAITING"
                        current_state['current_bids'] = {}
                        save_auction_state(current_state)
                        st.rerun()

    live_auction_board()
    
    if is_host:
        st.markdown("---")
        with st.expander(f"📋 잔여 경매 매물 전체 보기"):
            rem_pool = state.get('remaining_pool', [])
            if rem_pool:
                table_data = [{"아이디": user_dict[uid][0], "티어": user_dict[uid][3], "포지션": f"{user_dict[uid][4]}/{user_dict[uid][5]}"} for uid in rem_pool]
                st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        st.markdown("### 경매 종료 및 데이터베이스 저장")
        with st.form("save_auction_form"):
            num_teams = state['num_teams']
            if num_teams == 8:
                match_format = st.selectbox("대회 진행 방식", ["단판승부 (바로 DB 저장)", "조별리그 (4팀 2조, 조 1위 결승)", "풀리그 (모든 팀 상호 대전)", "토너먼트 (승자 진출)"])
            elif num_teams == 6:
                match_format = st.selectbox("대회 진행 방식", ["단판승부 (바로 DB 저장)", "조별리그 (3팀 2조, 조 1위 결승)", "풀리그 (모든 팀 상호 대전)", "토너먼트 (승자 진출)"])
            else:
                match_format = st.selectbox("대회 진행 방식", ["단판승부 (바로 DB 저장)", "풀리그 (모든 팀 상호 대전)", "토너먼트 (승자 진출)"])
                
            winning_team = st.selectbox("우승 팀 (단판승부용)", ["아직 모름"] + [t['name'] for t in state['teams']])
            save_btn = st.form_submit_button("대회 세션 확정", type="primary")
            
            if save_btn:
                players_data = []
                for team in state['teams']:
                    for m in team['members']:
                        players_data.append((m['user_id'], team['name'], m['role'], m['points_spent']))
                
                if "단판승부" in match_format:
                    database.add_match("AUCTION", state['host_name'], winning_team, players_data)
                else:
                    fmt = "GROUP_STAGE" if "조별리그" in match_format else "LEAGUE" if "풀리그" in match_format else "TOURNAMENT"
                    create_session(state['host_name'], state['teams'], players_data, fmt)
                    
                clear_auction_state()
                st.success("경매가 성공적으로 저장/종료되었습니다.")
                st.rerun()
                
        if st.button("❌ 경매 강제 초기화 (위험)", type="primary"):
            clear_auction_state()
            st.rerun()
