import streamlit as st
import sys
import os
import random
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from utils.tier_fetcher import calculate_clan_tier, abbreviate_tier
from utils.helpers import unpack_user_data, calculate_user_scores, format_user_for_selectbox, calculate_auction_points
from utils.tournament_manager import create_session

from utils.ui import set_background
from config import MIN_PLAYERS_REQUIRED, AUCTION_TEAM_OPTIONS

st.set_page_config(page_title="경매 내전", page_icon="💰", layout="wide")
if not st.session_state.get("auction_started", False):
    set_background("images (3).jpg")

st.markdown("""
<style>
div[data-testid="stToast"] {
    font-size: 1.1rem !important;
    background-color: #e6ffe6 !important;
    white-space: nowrap !important;
}
</style>
""", unsafe_allow_html=True)


st.title("💰 경매 내전")

if st.session_state.get("current_page") != "경매내전":
    st.toast('팀 배정 후 팀 확정 버튼 누르는거 잊지말아주세요~')
    st.session_state.current_page = "경매내전"

if st.session_state.get("auction_saved_toast", False):
    st.toast('내전 종료 후 내전이력에서 결과 등록 부탁드려요~')
    st.success("경매 내전 이력이 성공적으로 저장되었습니다!")
    st.session_state.auction_saved_toast = False

approved_users = database.get_all_approved_users()
auction_points, _ = database.get_auction_points_by_user()

if not approved_users or len(approved_users) < MIN_PLAYERS_REQUIRED:
    st.warning(f"승인된 회원이 {MIN_PLAYERS_REQUIRED}명 이상이어야 경매 내전을 진행할 수 있습니다.")
    st.stop()

# Helpers using helpers.py
def get_auction_points(tier_score):
    return calculate_auction_points(tier_score)

def format_user(user):
    return format_user_for_selectbox(user)

@st.cache_data(ttl=60)
def get_formatted_users(users):
    options = [format_user(u) for u in users]
    u_dict = {u[1]: u for u in options}
    return options, u_dict

user_options, user_dict = get_formatted_users(approved_users)

# Init session state for auction
if "auction_started" not in st.session_state:
    st.session_state.auction_started = False

if not st.session_state.auction_started:
    st.subheader("1. 경매 내전 설정")
    
    if os.path.exists("temp_save_auction.json"):
        if st.button("📂 임시저장된 경매내전 불러오기", use_container_width=True):
            try:
                with open("temp_save_auction.json", "r") as f:
                    data = json.load(f)
                for k, v in data.items():
                    st.session_state[k] = v
                st.success("임시저장 데이터를 불러왔습니다!")
                st.rerun()
            except:
                st.error("임시저장 파일을 불러오는데 실패했습니다.")
                
    st.markdown("#### 진행자 지정")
    host_mode = st.radio("진행자 입력 방식", ["회원 선택", "직접 입력"], horizontal=True)
    if host_mode == "회원 선택":
        host_id = st.selectbox("진행자 (회원)", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0].split('#')[0])
        host_name = user_dict[host_id][0].split('#')[0]
    else:
        host_name = st.text_input("진행자 (직접 입력)")
    
    # Select Participants first (outside the form to allow dynamic leader selection)
    st.markdown("#### 👤 경매 전체 참가자 선택 (팀장 포함)")
    selected_participants = st.multiselect(
        "이번 경매에 참가할 전체 선수들을 선택해주세요.",
        options=[u[1] for u in user_options],
        format_func=lambda x: user_dict[x][0]
    )

    # 팀 수 확정 버튼
    col_t1, col_t2 = st.columns([8, 2], vertical_alignment="bottom")
    with col_t1:
        num_teams_input = st.selectbox("팀 구성 수", [4, 6, 8])
    with col_t2:
        if st.button("팀 수 확정", use_container_width=True):
            st.session_state.num_teams_setup = num_teams_input
            
    num_teams = st.session_state.get("num_teams_setup", AUCTION_TEAM_OPTIONS[0])

    with st.form("auction_setup"):
        # Select team leaders from the participants
        st.markdown("#### 팀장 지정 (선택한 참가자 중에서 선택)")
        leaders = []
        cols = st.columns(3, vertical_alignment="bottom")
        for i in range(num_teams):
            with cols[i % 3]:
                leader = st.selectbox(f"Team {i+1} 팀장", options=[None] + selected_participants, format_func=lambda x: "선택안함" if x is None else user_dict[x][0], key=f"leader_{i}")
                leaders.append(leader)
                
        start_btn = st.form_submit_button("경매 시작")
        
        if start_btn:
            # Validations
            actual_leaders = [l for l in leaders if l is not None]
            if len(set(actual_leaders)) != len(actual_leaders):
                st.error("중복된 팀장이 있습니다.")
            elif not host_name:
                st.error("진행자를 지정해주세요.")
            elif not selected_participants:
                st.error("참가자를 1명 이상 선택해주세요.")
            else:
                st.session_state.auction_started = True
                st.session_state.host_name = host_name
                st.session_state.num_teams = num_teams
                
                # [DB] Pandas 연산 로직: 경매 시작 시점의 전체 참가자 초기 리스트 CSV 데이터 생성
                import pandas as pd
                csv_data = []
                for uid in selected_participants:
                    u_info = user_dict[uid]
                    raw_id = u_info[0]
                    if "] " in raw_id and " (" in raw_id:
                        raw_id = raw_id.split("] ")[1].split(" (")[0]
                    csv_data.append({
                        "아이디": raw_id,
                        "클랜티어": u_info[3],
                        "파워스코어": u_info[2],
                        "주포지션": u_info[4],
                        "부포지션": u_info[5]
                    })
                df = pd.DataFrame(csv_data)
                st.session_state.initial_csv = df.to_csv(index=False)
                
                # Init teams: list of dicts. each team has 'id', 'name', 'points', 'members'
                st.session_state.teams = []
                for i in range(num_teams):
                    leader_id = leaders[i]
                    members = []
                    team_points = 1000
                    if leader_id is not None:
                        members.append({'user_id': leader_id, 'points_spent': 0, 'role': 'Leader'})
                        leader_info = user_dict[leader_id]
                        leader_name = leader_info[0].split('#')[0] # use riot_id
                        team_points = get_auction_points(leader_info[2])
                    else:
                        leader_name = f"Team {i+1}"
                    
                    st.session_state.teams.append({
                        'id': i,
                        'name': f"{leader_name} 팀" if leader_id is not None else leader_name,
                        'points': team_points,
                        'members': members
                    })
                
                # Remaining pool (exclude actual leaders)
                st.session_state.remaining_pool = [p for p in selected_participants if p not in actual_leaders]
                st.session_state.skipped_pool = []
                st.session_state.current_target = None
                st.rerun()
else:
    # --- Auction In Progress ---
    # [UI] 버튼 네이밍 및 칸/줄 끝단 맞춤을 고려한 레이아웃 배치
    col_sub1, col_sub2 = st.columns([8, 2], vertical_alignment="bottom")
    with col_sub1:
        st.subheader(f"경매 진행 중 (진행자: {st.session_state.host_name})")
    with col_sub2:
        if "initial_csv" in st.session_state:
            st.download_button(
                "경매 매물 다운로드", 
                data=st.session_state.initial_csv.encode('utf-8-sig'), 
                file_name="초기_경매매물_리스트.csv", 
                mime="text/csv", 
                use_container_width=True,
                help="※ 본 명단은 경매 시작 시점의 초기 전체 리스트입니다. 실시간 상태는 반영되지 않습니다."
            )
    
    # Inject CSS for semi-transparent white background and black text for team containers
    st.markdown("""
    <style>
    /* Expander text center alignment */
    [data-testid="stExpander"] details summary {
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stExpander"] details summary > * {
        flex: 1 !important;
        text-align: center !important;
        display: flex !important;
        justify-content: center !important;
    }
    [data-testid="stExpander"] details summary svg {
        flex: 0 !important;
    }
    [data-testid="stExpander"] details summary p {
        width: 100% !important;
        text-align: center !important;
        font-weight: bold !important;
        display: inline-block !important;
    }
    /* Button text line break support */
    [data-testid="stButton"] p {
        white-space: pre-wrap !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # [UI] Render Teams (6팀일 땐 3열, 그 외엔 4열 배치)
    cols_per_row = 3 if st.session_state.num_teams == 6 else 4
    for row_start in range(0, st.session_state.num_teams, cols_per_row):
        cols = st.columns(cols_per_row, vertical_alignment="top")
        for col_idx in range(cols_per_row):
            if row_start + col_idx < st.session_state.num_teams:
                team = st.session_state.teams[row_start + col_idx]
                with cols[col_idx]:
                    html = f"""
                    <div style="background-color: #d1d6df; border-radius: 8px; padding: 6px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); border: 1px solid #a3aab5; min-height: 110px; margin-bottom: 10px;">
                        <div style="font-size: 0.95rem; font-weight: bold; text-align: center; color: #000; margin-bottom: 2px;">{team['name']}</div>
                        <div style="font-size: 0.9rem; font-weight: bold; text-align: center; color: #d32f2f; margin-bottom: 4px;">잔여 P: {team['points']}</div>
                        <hr style="margin: 2px 0 4px 0; border: 0; border-top: 2px solid #999;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; padding: 2px 0;">
                    """
                    for m in team['members']:
                        if m['role'] == 'Leader':
                            continue
                            
                        raw_name_full = user_dict[m['user_id']][0]
                        clean_name = raw_name_full.split(' (')[0] if ' (' in raw_name_full else raw_name_full
                        clean_name = clean_name.split('#')[0]
                        if '] ' in clean_name:
                            clean_name = clean_name.split('] ')[-1]
                        
                        html += f"<div style='font-size: 0.75rem; color: #000; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>- {clean_name} ({m['points_spent']})</div>"
                    
                    html += "</div></div>"
                    st.markdown(html, unsafe_allow_html=True)
                
    st.markdown("<hr style='margin: 10px 0; border: 0; border-top: 1px solid #ccc;'>", unsafe_allow_html=True)
    
    # Auction Control
    col1, col2 = st.columns([1, 1], vertical_alignment="top")
    
    with col1:
        st.markdown("### 랜덤 뽑기")
        st.write(f"남은 인원: {len(st.session_state.remaining_pool)}명 / 유찰: {len(st.session_state.skipped_pool)}명")
        
        if st.button("🎲 다음 참가자 뽑기", type="primary"):
            if st.session_state.remaining_pool:
                target = random.choice(st.session_state.remaining_pool)
                st.session_state.current_target = target
                st.rerun()
            else:
                st.warning("더 이상 남은 참가자가 없습니다.")
                
        if st.session_state.current_target:
            t_user = user_dict[st.session_state.current_target]
            total_points = auction_points.get(t_user[1], 0) + t_user[6]
            trophies = total_points // 25
            medals = (total_points % 25) // 5
            stars = total_points % 5
            
            symbol_str = ""
            if trophies > 0: symbol_str += "🏆" * trophies
            if medals > 0: symbol_str += "🎖️" * medals
            if stars > 0: symbol_str += "⭐" * stars
            if not symbol_str: symbol_str = "-"
            
            st.markdown(f"""
            <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 1rem;">
                <div style="font-size: 80%; line-height: 1.8; color: #333;">
                    <span style="font-size: 1.2em; font-weight: bold; color: #000;">🎯 현재 대상: {t_user[0]}</span><br>
                    <div style="margin-left: 5px; margin-top: 5px;">
                        <b>🌟 우승 기록:</b> {symbol_str}<br>
                        <b>🏆 클랜 티어:</b> {t_user[3]}<br>
                        <b>⚔️ 포지션:</b> 주 <b>{t_user[4]}</b> | 부 <b>{t_user[5]}</b>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action: Skip
            if st.button("⏭️ 유찰 (다음 뽑기에서 제외)"):
                st.session_state.remaining_pool.remove(st.session_state.current_target)
                st.session_state.skipped_pool.append(st.session_state.current_target)
                st.session_state.current_target = None
                st.rerun()
                
    with col2:
        if st.session_state.current_target:
            st.markdown("### 낙찰 입력")
            bid_points = st.number_input("소모 포인트", min_value=0, max_value=1000, value=0, step=10)
            st.markdown("<span style='font-size: 70%; font-weight: bold;'>낙찰 팀 (클릭 시 즉시 배정)</span>", unsafe_allow_html=True)
            
            # [UI] 낙찰 버튼도 팀 배치와 동일하게 3열 또는 4열로 컴팩트하게 배치
            cols_per_row = 3 if st.session_state.num_teams == 6 else 4
            for row_start in range(0, st.session_state.num_teams, cols_per_row):
                cols_team = st.columns(cols_per_row, vertical_alignment="bottom")
                for col_idx in range(cols_per_row):
                    if row_start + col_idx < st.session_state.num_teams:
                        t_idx = row_start + col_idx
                        team = st.session_state.teams[t_idx]
                        with cols_team[col_idx]:
                            if st.button(f"{team['name']}\n({team['points']}p, {len(team['members'])}/5)", key=f"bid_team_{t_idx}", use_container_width=True):
                                if len(team['members']) >= 5:
                                    st.error("해당 팀은 이미 5명의 인원이 꽉 찼습니다.")
                                elif team['points'] < bid_points:
                                    st.error("팀의 남은 포인트가 부족합니다.")
                                else:
                                    st.session_state.teams[t_idx]['points'] -= bid_points
                                    st.session_state.teams[t_idx]['members'].append({
                                        'user_id': st.session_state.current_target,
                                        'points_spent': bid_points,
                                        'role': 'Member'
                                    })
                                    st.session_state.remaining_pool.remove(st.session_state.current_target)
                                    st.session_state.current_target = None
                                    st.rerun()
                        
    st.markdown("<hr style='margin: 10px 0; border: 0; border-top: 1px solid #ccc;'>", unsafe_allow_html=True)
    
    # Skipped Pool Manual Allocation
    if st.session_state.skipped_pool:
        st.markdown("### 유찰자 수동 배정 (재경매)")
        for idx, skip_user_id in enumerate(st.session_state.skipped_pool):
            skip_user = user_dict[skip_user_id]
            st.markdown(f"<span style='font-size: 70%; font-weight: bold;'>- {skip_user[0]}</span>", unsafe_allow_html=True)
            
            bid_points = st.number_input("소모 포인트", min_value=0, max_value=1000, value=0, step=10, key=f"skip_bid_{idx}")
            
            available_teams = [t for t in st.session_state.teams if len(t['members']) < 5]
            if not available_teams:
                st.warning("배정 가능한 팀이 없습니다.")
            else:
                cols_skip = st.columns(len(available_teams), vertical_alignment="bottom")
                for t_idx, target_team in enumerate(available_teams):
                    with cols_skip[t_idx]:
                        if st.button(f"{target_team['name']}\n({target_team['points']}p, {len(target_team['members'])}명)", key=f"skip_{idx}_team_{target_team['id']}", use_container_width=True):
                            real_idx = st.session_state.teams.index(target_team)
                            if st.session_state.teams[real_idx]['points'] < bid_points:
                                st.error("팀의 남은 포인트가 부족합니다.")
                            else:
                                st.session_state.teams[real_idx]['points'] -= bid_points
                                st.session_state.teams[real_idx]['members'].append({
                                    'user_id': skip_user_id,
                                    'points_spent': bid_points,
                                    'role': 'Member'
                                })
                                st.session_state.skipped_pool.remove(skip_user_id)
                                st.rerun()
            st.markdown("---")
                        
    st.markdown("<hr style='margin: 10px 0; border: 0; border-top: 1px solid #ccc;'>", unsafe_allow_html=True)
    
    # [UI] 하단 숨김 구역: 잔여 매물 전체 보기
    with st.expander(f"📋 잔여 경매 매물 전체 보기 (현재 남은 인원: {len(st.session_state.remaining_pool)}명)"):
        if st.session_state.remaining_pool:
            import pandas as pd
            table_data = []
            for uid in st.session_state.remaining_pool:
                user = user_dict[uid]
                raw_id = user[0]
                if "] " in raw_id and " (" in raw_id:
                    raw_id = raw_id.split("] ")[1].split(" (")[0]
                table_data.append({
                    "아이디": raw_id,
                    "클랜티어": user[3],
                    "파워스코어": user[2],
                    "주포지션": user[4],
                    "부포지션": user[5]
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("남은 매물이 없습니다.")

    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    
    with col_c2:
        # 하단 수정 기능 통합 패널
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if "show_edit_panel" not in st.session_state:
                st.session_state.show_edit_panel = False
            if st.button("🛠️ 팀원/포인트 배정 수정", use_container_width=True):
                st.session_state.show_edit_panel = not st.session_state.show_edit_panel
                st.session_state.show_points_panel = False
                st.rerun()
        with col_e2:
            if "show_points_panel" not in st.session_state:
                st.session_state.show_points_panel = False
            if st.button("⚙️ 잔여 포인트 임의 수정", use_container_width=True):
                st.session_state.show_points_panel = not st.session_state.show_points_panel
                st.session_state.show_edit_panel = False
                st.rerun()
                
        if st.session_state.show_edit_panel:
            with st.container(border=True):
                # Get all assigned non-leader members
                assigned_members = []
                for t_idx, team in enumerate(st.session_state.teams):
                    for m_idx, m in enumerate(team['members']):
                        if m['role'] != 'Leader':
                            assigned_members.append({
                                'team_idx': t_idx,
                                'member_idx': m_idx,
                                'user_id': m['user_id'],
                                'points_spent': m['points_spent'],
                                'name': user_dict[m['user_id']][0]
                            })
                
                if not assigned_members:
                    st.info("현재 배정된 팀원이 없습니다.")
                else:
                    col_e1, col_e2 = st.columns(2, vertical_alignment="bottom")
                    with col_e1:
                        def format_member(m):
                            t_name = st.session_state.teams[m['team_idx']]['name']
                            return f"[{t_name}] {m['name']} ({m['points_spent']}p)"
                        
                        selected_m = st.selectbox("수정할 팀원 선택", assigned_members, format_func=format_member)
                        st.write(f"현재 소속: **{st.session_state.teams[selected_m['team_idx']]['name']}**")
                        
                    with col_e2:
                        team_names = [t['name'] for t in st.session_state.teams]
                        new_team_name = st.selectbox("새로 배정할 팀", team_names, index=selected_m['team_idx'])
                        new_team_idx = team_names.index(new_team_name)
                        
                        new_pts = st.number_input("새로운 소모 포인트", min_value=0, max_value=1000, value=selected_m['points_spent'], step=10, key="edit_pts")
                        
                    if st.button("배정 수정 적용", type="primary", use_container_width=True):
                        old_t_idx = selected_m['team_idx']
                        m_idx = selected_m['member_idx']
                        old_pts = selected_m['points_spent']
                        
                        old_team = st.session_state.teams[old_t_idx]
                        new_team = st.session_state.teams[new_team_idx]
                        
                        if old_t_idx == new_team_idx:
                            if old_team['points'] + old_pts < new_pts:
                                st.error("팀의 남은 포인트가 부족합니다.")
                            else:
                                old_team['points'] += old_pts
                                old_team['points'] -= new_pts
                                old_team['members'][m_idx]['points_spent'] = new_pts
                                st.success("포인트가 수정되었습니다.")
                                st.rerun()
                        else:
                            if len(new_team['members']) >= 5:
                                st.error("새로운 팀은 이미 5명의 인원이 꽉 찼습니다.")
                            elif new_team['points'] < new_pts:
                                st.error("새로운 팀의 남은 포인트가 부족합니다.")
                            else:
                                old_team['points'] += old_pts
                                member_data = old_team['members'].pop(m_idx)
                                new_team['points'] -= new_pts
                                member_data['points_spent'] = new_pts
                                new_team['members'].append(member_data)
                                st.success("팀 배정이 수정되었습니다.")
                                st.rerun()
                                
        if st.session_state.get('show_points_panel', False):
            with st.container(border=True):
                st.markdown("#### 팀 잔여 포인트 직접 수정")
                col_p1, col_p2 = st.columns(2, vertical_alignment="bottom")
                with col_p1:
                    team_names = [t['name'] for t in st.session_state.teams]
                    selected_team = st.selectbox("포인트를 수정할 팀", team_names)
                    sel_idx = team_names.index(selected_team)
                with col_p2:
                    current_p = st.session_state.teams[sel_idx]['points']
                    new_team_pts = st.number_input("수정할 포인트 값", value=current_p, step=10, key="edit_team_pts")
                    
                if st.button("팀 포인트 수정 적용", type="primary", use_container_width=True):
                    st.session_state.teams[sel_idx]['points'] = new_team_pts
                    st.success(f"{selected_team}의 잔여 포인트가 {new_team_pts}로 수정되었습니다.")
                    st.rerun()

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("💾 현재 경매상태 임시저장", use_container_width=True):
            data = {
                'auction_started': st.session_state.auction_started,
                'host_name': st.session_state.host_name,
                'num_teams': st.session_state.num_teams,
                'teams': st.session_state.teams,
                'remaining_pool': st.session_state.remaining_pool,
                'skipped_pool': st.session_state.skipped_pool,
                'current_target': st.session_state.current_target,
                'initial_csv': st.session_state.get('initial_csv', '')
            }
            with open("temp_save_auction.json", "w") as f:
                json.dump(data, f)
            st.success("현재 경매 진행 상황이 임시저장 되었습니다!")
            
    st.markdown("### 경매 종료 및 저장")
    with st.form("save_auction_form"):
        if st.session_state.num_teams == 8:
            match_format = st.selectbox("대회 진행 방식", ["단판승부 (바로 DB 저장)", "조별리그 (4팀 2조, 조 1위 결승)", "풀리그 (모든 팀 상호 대전)", "토너먼트 (승자 진출)"])
        elif st.session_state.num_teams == 6:
            match_format = st.selectbox("대회 진행 방식", ["단판승부 (바로 DB 저장)", "조별리그 (3팀 2조, 조 1위 결승)", "풀리그 (모든 팀 상호 대전)", "토너먼트 (승자 진출)"])
        else:
            match_format = st.selectbox("대회 진행 방식", ["단판승부 (바로 DB 저장)", "풀리그 (모든 팀 상호 대전)", "토너먼트 (승자 진출)"])
            
        winning_team = st.selectbox("우승 팀 (단판승부용 이력 보관)", ["아직 모름"] + [t['name'] for t in st.session_state.teams])
        save_btn = st.form_submit_button("대회 세션 확정", type="primary")
        
        if save_btn:
            players_data = []
            for team in st.session_state.teams:
                for m in team['members']:
                    players_data.append((m['user_id'], team['name'], m['role'], m['points_spent']))
            
            if "단판승부" in match_format:
                database.add_match("AUCTION", st.session_state.host_name, winning_team, players_data)
                st.session_state.auction_saved_toast = True
            else:
                if "조별리그" in match_format:
                    fmt = "GROUP_STAGE"
                elif "풀리그" in match_format:
                    fmt = "LEAGUE"
                else:
                    fmt = "TOURNAMENT"
                create_session(st.session_state.host_name, st.session_state.teams, players_data, fmt)
                st.session_state.auction_saved_toast = True
                
            if os.path.exists("temp_save_auction.json"):
                os.remove("temp_save_auction.json")
                
            # Reset state
            st.session_state.auction_started = False
            del st.session_state.host_name
            del st.session_state.num_teams
            del st.session_state.teams
            del st.session_state.remaining_pool
            del st.session_state.skipped_pool
            del st.session_state.current_target
            if "initial_csv" in st.session_state:
                del st.session_state.initial_csv
            st.rerun()
