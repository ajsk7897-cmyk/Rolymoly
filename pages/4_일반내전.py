import streamlit as st
import sys
import os
import itertools
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from utils.tier_fetcher import calculate_clan_tier, abbreviate_tier
from utils.helpers import unpack_user_data, calculate_user_scores, format_user_for_selectbox
from utils.tournament_manager import create_session

from config import MIN_PLAYERS_REQUIRED, DEFAULT_ROLES

st.set_page_config(page_title="일반 내전", page_icon="⚔️", layout="wide")

st.markdown("""
<style>
div[data-testid="stToast"] {
    font-size: 1.1rem !important;
    background-color: #e6ffe6 !important;
    white-space: nowrap !important;
}
</style>
""", unsafe_allow_html=True)


st.title("⚔️ 일반 내전 (10인 밸런스 매칭)")

if st.session_state.get("current_page") != "일반내전":
    st.toast('팀 배정 후 팀 확정 버튼 누르는거 잊지말아주세요~')
    st.session_state.current_page = "일반내전"

if st.session_state.get("normal_saved_toast", False):
    st.toast('내전 종료 후 내전이력에서 결과 등록 부탁드려요~')
    st.success("내전 이력이 성공적으로 저장되었습니다!")
    st.session_state.normal_saved_toast = False

st.markdown("라인별로 2명씩 총 10명의 참가자를 선택하면, 파워스코어 차이가 최소화되도록 팀을 자동 배정합니다.")

approved_users = database.get_all_approved_users()

if not approved_users or len(approved_users) < MIN_PLAYERS_REQUIRED:
    st.warning(f"승인된 회원이 {MIN_PLAYERS_REQUIRED}명 이상이어야 내전을 진행할 수 있습니다.")
    st.stop()

# Helper to format user for selectbox using helpers
def format_user(user):
    user_dict = unpack_user_data(user)
    _, final_score, clan_tier = calculate_user_scores(user_dict)
    abbr_tier = abbreviate_tier(clan_tier)
    return f"[{abbr_tier}] {user_dict['riot_id']}#{user_dict['tag_line']} (스코어: {final_score})", user_dict['user_id'], final_score, user_dict['riot_id']

@st.cache_data(ttl=60)
def get_formatted_users_for_normal(users):
    options = [format_user(u) for u in users]
    u_dict = {u[1]: u for u in options}
    return options, u_dict

user_options, user_dict = get_formatted_users_for_normal(approved_users)

roles = DEFAULT_ROLES

tab1, tab2 = st.tabs(["일반내전 (10인)", "일반내전 (20인)"])

def render_tab1():
    st.subheader("1. 참가자 및 진행자 선택")

    if os.path.exists("temp_save_normal.json"):
        if st.button("📂 임시저장된 팀 배정 불러오기", use_container_width=True):
            try:
                with open("temp_save_normal.json", "r") as f:
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
        host_id = st.selectbox("진행자 (회원)", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0].split('#')[0] if x else "선택 없음", index=None, placeholder="참가자 입력")
        host_name = user_dict[host_id][0].split('#')[0] if host_id else None
    else:
        host_name = st.text_input("진행자 (직접 입력)")

    selected_players = {}

    with st.form("participant_form"):
        cols = st.columns(5, vertical_alignment="bottom")
        for i, role in enumerate(roles):
            with cols[i]:
                st.markdown(f"**{role}**")
                p1 = st.selectbox(f"{role} 1", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0], key=f"sel_{role}_1", index=None, placeholder="참가자 입력")
                p2 = st.selectbox(f"{role} 2", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0], key=f"sel_{role}_2", index=None, placeholder="참가자 입력")
                selected_players[role] = [p1, p2]
                
        col_submit1, col_submit2 = st.columns(2, vertical_alignment="bottom")
        with col_submit1:
            submit_participants_balance = st.form_submit_button("팀 밸런스 맞추기", use_container_width=True)
        with col_submit2:
            submit_participants_manual = st.form_submit_button("입력한 팀으로 바로 확정", use_container_width=True)

    if submit_participants_balance or submit_participants_manual:
        # Check for duplicates
        all_selected = []
        for role, players in selected_players.items():
            all_selected.extend(players)
            
        # 방어 로직 (Validation)
        if any(p is None for p in all_selected):
            st.warning("모든 라인의 참가자를 선택해주세요.")
            return
            
        if host_mode == "회원 선택" and not host_id:
            st.warning("진행자를 선택해주세요.")
            return
            
        if len(set(all_selected)) < 10:
            st.error("중복된 참가자가 있습니다. 각 포지션에 다른 유저를 선택해주세요.")
        elif not host_name:
            st.error("진행자 이름을 입력해주세요.")
        else:
            # Store in session state to show the result
            st.session_state.match_participants = selected_players
            st.session_state.match_host = host_name
            
            if submit_participants_balance:
                # Calculate optimal balance
                # We need to pick 1 from each role for Team A, the other goes to Team B
                best_diff = float('inf')
                best_team_a = {}
                best_team_b = {}
                
                # 2^5 = 32 combinations. 0 means first player, 1 means second player
                for combo in itertools.product([0, 1], repeat=5):
                    team_a_score = 0
                    team_b_score = 0
                    temp_a = {}
                    temp_b = {}
                    
                    for i, role in enumerate(roles):
                        a_idx = combo[i]
                        b_idx = 1 - a_idx
                        
                        a_user_id = selected_players[role][a_idx]
                        b_user_id = selected_players[role][b_idx]
                        
                        temp_a[role] = a_user_id
                        temp_b[role] = b_user_id
                        
                        team_a_score += user_dict[a_user_id][2]
                        team_b_score += user_dict[b_user_id][2]
                        
                    diff = abs(team_a_score - team_b_score)
                    if diff < best_diff:
                        best_diff = diff
                        best_team_a = temp_a
                        best_team_b = temp_b
                        
                st.session_state.team_a = best_team_a
                st.session_state.team_b = best_team_b
            elif submit_participants_manual:
                st.session_state.team_a = {role: selected_players[role][0] for role in roles}
                st.session_state.team_b = {role: selected_players[role][1] for role in roles}
                
            st.rerun()

    if "team_a" in st.session_state:
        st.divider()
        st.subheader("2. 팀 배정 결과 및 조정")
        
        # Calculate current scores based on session_state.team_a and team_b
        def get_team_score(team):
            return sum([user_dict[uid][2] for uid in team.values()])
        
        score_a = get_team_score(st.session_state.team_a)
        score_b = get_team_score(st.session_state.team_b)
        
        col1, col2 = st.columns(2, vertical_alignment="bottom")
        
        with col1:
            st.markdown(f"### 🔵 Team A (총점: {score_a}점)")
            for role in roles:
                uid = st.session_state.team_a[role]
                st.info(f"**{role}**: {user_dict[uid][0]}")
                
        with col2:
            st.markdown(f"### 🔴 Team B (총점: {score_b}점)")
            for role in roles:
                uid = st.session_state.team_b[role]
                st.error(f"**{role}**: {user_dict[uid][0]}")
                
        st.write(f"**두 팀의 점수 차이**: {abs(score_a - score_b)}점")
        
        st.markdown("---")
        st.markdown("#### 수동 팀 조정 (스왑)")
        swap_role = st.selectbox("스왑할 라인 선택", roles)
        if st.button(f"{swap_role} 라인 스왑하기"):
            # Swap
            st.session_state.team_a[swap_role], st.session_state.team_b[swap_role] = st.session_state.team_b[swap_role], st.session_state.team_a[swap_role]
            st.rerun()

        st.markdown("---")
        
        col_t1, col_t2 = st.columns(2, vertical_alignment="bottom")
        with col_t1:
            if st.button("💾 현재 상태 임시저장", use_container_width=True):
                data = {
                    'team_a': st.session_state.team_a,
                    'team_b': st.session_state.team_b,
                    'match_participants': st.session_state.match_participants,
                    'match_host': st.session_state.match_host
                }
                with open("temp_save_normal.json", "w") as f:
                    json.dump(data, f)
                st.success("현재 팀 배정 상태가 임시저장 되었습니다!")
        
        if "confirm_step_1" not in st.session_state:
            st.session_state.confirm_step_1 = False
            
        winning_team = st.selectbox("승리 팀 기록 (선택)", ["아직 모름", "Team A", "Team B"])
        
        if st.button("팀 확정 및 DB 저장", type="primary"):
            st.session_state.confirm_step_1 = True
            
        if st.session_state.confirm_step_1:
            st.warning("⚠️ 전적을 최종 확정하시겠습니까? (이 작업은 되돌릴 수 없습니다)")
            col_c1, col_c2 = st.columns([1, 1], vertical_alignment="bottom")
            with col_c1:
                if st.button("✅ 네, 확정합니다", type="primary", use_container_width=True):
                    players_data = []
                    for role in roles:
                        players_data.append((st.session_state.team_a[role], "Team A", role, 0))
                        players_data.append((st.session_state.team_b[role], "Team B", role, 0))
                    
                    database.add_match("NORMAL", st.session_state.match_host, winning_team, players_data)
                    st.session_state.normal_saved_toast = True
                    
                    if os.path.exists("temp_save_normal.json"):
                        os.remove("temp_save_normal.json")
                    
                    # Clear state
                    st.session_state.confirm_step_1 = False
                    del st.session_state.team_a
                    del st.session_state.team_b
                    del st.session_state.match_participants
                    del st.session_state.match_host
                    st.rerun()
                    
            with col_c2:
                if st.button("❌ 취소", use_container_width=True):
                    st.session_state.confirm_step_1 = False
                    st.rerun()

def render_tab2():
    st.subheader("1. 참가자 및 진행자 선택 (20인)")

    if os.path.exists("temp_save_normal_20.json"):
        if st.button("📂 임시저장된 팀 배정 불러오기", key="btn_load_20", use_container_width=True):
            try:
                with open("temp_save_normal_20.json", "r") as f:
                    data = json.load(f)
                for k, v in data.items():
                    st.session_state[k] = v
                st.success("임시저장 데이터를 불러왔습니다!")
                st.rerun()
            except:
                st.error("임시저장 파일을 불러오는데 실패했습니다.")

    st.markdown("#### 진행자 지정")
    host_mode = st.radio("진행자 입력 방식", ["회원 선택", "직접 입력"], horizontal=True, key="host_mode_20")
    if host_mode == "회원 선택":
        host_id = st.selectbox("진행자 (회원)", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0].split('#')[0] if x else "선택 없음", index=None, placeholder="참가자 입력", key="host_id_20")
        host_name = user_dict[host_id][0].split('#')[0] if host_id else None
    else:
        host_name = st.text_input("진행자 (직접 입력)", key="host_name_20")

    selected_players = {}

    with st.form("participant_form_20"):
        cols = st.columns(5, vertical_alignment="bottom")
        for i, role in enumerate(roles):
            with cols[i]:
                st.markdown(f"**{role}**")
                p1 = st.selectbox(f"{role} 1", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0], key=f"sel20_{role}_1", index=None, placeholder="참가자 입력")
                p2 = st.selectbox(f"{role} 2", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0], key=f"sel20_{role}_2", index=None, placeholder="참가자 입력")
                p3 = st.selectbox(f"{role} 3", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0], key=f"sel20_{role}_3", index=None, placeholder="참가자 입력")
                p4 = st.selectbox(f"{role} 4", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0], key=f"sel20_{role}_4", index=None, placeholder="참가자 입력")
                selected_players[role] = [p1, p2, p3, p4]
                
        col_submit1, col_submit2 = st.columns(2, vertical_alignment="bottom")
        with col_submit1:
            submit_participants_balance = st.form_submit_button("팀 밸런스 맞추기", use_container_width=True)
        with col_submit2:
            submit_participants_manual = st.form_submit_button("입력한 팀으로 바로 확정", use_container_width=True)

    if submit_participants_balance or submit_participants_manual:
        all_selected = []
        for role, players in selected_players.items():
            all_selected.extend(players)
            
        if any(p is None for p in all_selected):
            st.warning("모든 라인의 참가자 20명을 전부 선택해주세요.")
            return
            
        if host_mode == "회원 선택" and not host_id:
            st.warning("진행자를 선택해주세요.")
            return
            
        if len(set(all_selected)) < 20:
            st.error("중복된 참가자가 있습니다. 각 포지션에 다른 유저를 선택해주세요.")
        elif not host_name:
            st.error("진행자 이름을 입력해주세요.")
        else:
            st.session_state.match_participants_20 = selected_players
            st.session_state.match_host_20 = host_name
            
            if submit_participants_balance:
                best_diff = float('inf')
                best_teams = []
                
                base_perm = (0, 1, 2, 3)
                
                scores = {}
                for role in roles:
                    scores[role] = [user_dict[selected_players[role][i]][2] for i in range(4)]

                import itertools
                perms = list(itertools.permutations([0, 1, 2, 3]))
                
                for p1 in perms:
                    for p2 in perms:
                        for p3 in perms:
                            for p4 in perms:
                                combo = [base_perm, p1, p2, p3, p4]
                                
                                team_scores = [0, 0, 0, 0]
                                for r_idx, role_perm in enumerate(combo):
                                    role = roles[r_idx]
                                    for team_idx in range(4):
                                        p_idx = role_perm[team_idx]
                                        team_scores[team_idx] += scores[role][p_idx]
                                
                                diff = max(team_scores) - min(team_scores)
                                if diff < best_diff:
                                    best_diff = diff
                                    best_teams = combo
                                    if diff == 0:
                                        break
                            if best_diff == 0: break
                        if best_diff == 0: break
                    if best_diff == 0: break
                
                teams = [{'dict': {}}, {'dict': {}}, {'dict': {}}, {'dict': {}}]
                for r_idx, role_perm in enumerate(best_teams):
                    role = roles[r_idx]
                    for team_idx in range(4):
                        p_idx = role_perm[team_idx]
                        teams[team_idx]['dict'][role] = selected_players[role][p_idx]
                
                st.session_state.team_a_20 = teams[0]['dict']
                st.session_state.team_b_20 = teams[1]['dict']
                st.session_state.team_c_20 = teams[2]['dict']
                st.session_state.team_d_20 = teams[3]['dict']
                
            elif submit_participants_manual:
                st.session_state.team_a_20 = {role: selected_players[role][0] for role in roles}
                st.session_state.team_b_20 = {role: selected_players[role][1] for role in roles}
                st.session_state.team_c_20 = {role: selected_players[role][2] for role in roles}
                st.session_state.team_d_20 = {role: selected_players[role][3] for role in roles}
                
            st.rerun()

    if "team_a_20" in st.session_state:
        st.divider()
        st.subheader("2. 팀 배정 결과 및 조정 (20인)")
        
        def get_team_score(team):
            return sum([user_dict[uid][2] for uid in team.values()])
            
        def get_team_name(team_dict, default_name):
            top_uid = team_dict.get("TOP")
            if top_uid and top_uid in user_dict:
                return f"{user_dict[top_uid][3]}팀"
            return default_name

        team_a_name = get_team_name(st.session_state.team_a_20, "Team A")
        team_b_name = get_team_name(st.session_state.team_b_20, "Team B")
        team_c_name = get_team_name(st.session_state.team_c_20, "Team C")
        team_d_name = get_team_name(st.session_state.team_d_20, "Team D")
        
        scores = [
            get_team_score(st.session_state.team_a_20),
            get_team_score(st.session_state.team_b_20),
            get_team_score(st.session_state.team_c_20),
            get_team_score(st.session_state.team_d_20)
        ]
        
        col1, col2, col3, col4 = st.columns(4, vertical_alignment="bottom")
        
        teams_data = [
            (team_a_name, st.session_state.team_a_20, col1, "🔵", "A"),
            (team_b_name, st.session_state.team_b_20, col2, "🔴", "B"),
            (team_c_name, st.session_state.team_c_20, col3, "🟡", "C"),
            (team_d_name, st.session_state.team_d_20, col4, "🟢", "D")
        ]
        
        for idx, (name, team_dict, col, icon, raw_name) in enumerate(teams_data):
            with col:
                st.markdown(f"### {icon} {name} (총점: {scores[idx]}점)")
                for role in roles:
                    uid = team_dict[role]
                    st.info(f"**{role}**: {user_dict[uid][0]}")
                
        st.write(f"**최대-최소 점수 차이**: {max(scores) - min(scores)}점")
        
        st.markdown("---")
        st.markdown("#### 수동 팀 조정 (스왑)")
        swap_col1, swap_col2, swap_col3, swap_col4 = st.columns([2, 2, 2, 2], vertical_alignment="bottom")
        
        team_keys = {
            team_a_name: "a",
            team_b_name: "b",
            team_c_name: "c",
            team_d_name: "d"
        }
        
        with swap_col1:
            swap_team1 = st.selectbox("변경할 팀 1", list(team_keys.keys()), key="swap_team1_20")
        with swap_col2:
            swap_team2 = st.selectbox("변경할 팀 2", list(team_keys.keys()), index=1, key="swap_team2_20")
        with swap_col3:
            swap_role_20 = st.selectbox("스왑할 라인 선택", roles, key="swap_role_20")
        with swap_col4:
            if st.button("라인 스왑하기", use_container_width=True, key="btn_swap_20"):
                if swap_team1 != swap_team2:
                    t1_key = f"team_{team_keys[swap_team1]}_20"
                    t2_key = f"team_{team_keys[swap_team2]}_20"
                    
                    st.session_state[t1_key][swap_role_20], st.session_state[t2_key][swap_role_20] = \
                        st.session_state[t2_key][swap_role_20], st.session_state[t1_key][swap_role_20]
                    st.rerun()
                else:
                    st.warning("서로 다른 두 팀을 선택해주세요.")

        st.markdown("---")
        
        col_t1, col_t2 = st.columns(2, vertical_alignment="bottom")
        with col_t1:
            if st.button("💾 현재 상태 임시저장", use_container_width=True, key="save_20"):
                data = {
                    'team_a_20': st.session_state.team_a_20,
                    'team_b_20': st.session_state.team_b_20,
                    'team_c_20': st.session_state.team_c_20,
                    'team_d_20': st.session_state.team_d_20,
                    'match_participants_20': st.session_state.match_participants_20,
                    'match_host_20': st.session_state.match_host_20
                }
                with open("temp_save_normal_20.json", "w") as f:
                    json.dump(data, f)
                st.success("현재 팀 배정 상태가 임시저장 되었습니다!")
        
        if "confirm_step_1_20" not in st.session_state:
            st.session_state.confirm_step_1_20 = False
            
        match_format_20 = st.selectbox("대회 진행 방식", ["단판승부 (바로 DB 저장)", "풀리그 (모든 팀 상호 대전)", "토너먼트 (승자 진출)"], key="format_20")
        winning_team = st.selectbox("우승 팀 (단판승부용 이력 보관)", ["아직 모름", team_a_name, team_b_name, team_c_name, team_d_name], key="win_20")
        
        if st.button("대회 세션 확정", type="primary", key="confirm_btn_20"):
            st.session_state.confirm_step_1_20 = True
            
        if st.session_state.confirm_step_1_20:
            st.warning("⚠️ 전적을 최종 확정하시겠습니까? (이 작업은 되돌릴 수 없습니다)")
            col_c1, col_c2 = st.columns([1, 1], vertical_alignment="bottom")
            with col_c1:
                if st.button("✅ 네, 확정합니다", type="primary", use_container_width=True, key="confirm_yes_20"):
                    players_data = []
                    for role in roles:
                        players_data.append((st.session_state.team_a_20[role], team_a_name, role, 0))
                        players_data.append((st.session_state.team_b_20[role], team_b_name, role, 0))
                        players_data.append((st.session_state.team_c_20[role], team_c_name, role, 0))
                        players_data.append((st.session_state.team_d_20[role], team_d_name, role, 0))
                    
                    if "단판승부" in match_format_20:
                        database.add_match("NORMAL", st.session_state.match_host_20, winning_team, players_data)
                        st.session_state.normal_saved_toast = True
                    else:
                        fmt = "LEAGUE" if "풀리그" in match_format_20 else "TOURNAMENT"
                        teams = []
                        teams_data_db = [
                            (0, team_a_name, st.session_state.team_a_20),
                            (1, team_b_name, st.session_state.team_b_20),
                            (2, team_c_name, st.session_state.team_c_20),
                            (3, team_d_name, st.session_state.team_d_20),
                        ]
                        for tid, tname, tdict in teams_data_db:
                            members = []
                            for r, uid in tdict.items():
                                members.append({'user_id': uid, 'points_spent': 0, 'role': r})
                            teams.append({
                                'id': tid,
                                'name': tname,
                                'points': 0,
                                'members': members
                            })
                        create_session(st.session_state.match_host_20, teams, players_data, fmt, "NORMAL")
                        st.session_state.normal_saved_toast = True
                    
                    if os.path.exists("temp_save_normal_20.json"):
                        os.remove("temp_save_normal_20.json")
                    
                    st.session_state.confirm_step_1_20 = False
                    for k in ['team_a_20', 'team_b_20', 'team_c_20', 'team_d_20', 'match_participants_20', 'match_host_20']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()
                    
            with col_c2:
                if st.button("❌ 취소", use_container_width=True, key="confirm_no_20"):
                    st.session_state.confirm_step_1_20 = False
                    st.rerun()

with tab1:
    render_tab1()

with tab2:
    render_tab2()
