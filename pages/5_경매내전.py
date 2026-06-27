import streamlit as st
import sys
import os
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

st.set_page_config(page_title="경매 내전", page_icon="💰", layout="wide")

st.title("💰 경매 내전")

approved_users = database.get_all_approved_users()
if not approved_users or len(approved_users) < 10:
    st.warning("승인된 회원이 부족하여 경매 내전을 진행할 수 없습니다.")
    st.stop()

from utils.tier_fetcher import calculate_clan_tier

# Helpers
def format_user(user):
    if len(user) == 12:
        user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus, main_pos, sub_pos = user
    else:
        user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus = user
        main_pos, sub_pos = "", ""
    final_score = (manual_score if manual_score != -1 else power_score) + match_bonus
    clan_tier = calculate_clan_tier(final_score)
    return f"{riot_id}#{tag_line} (스코어: {final_score})", user_id, final_score, clan_tier, main_pos, sub_pos

user_options = [format_user(u) for u in approved_users]
user_dict = {u[1]: u for u in user_options}

# Init session state for auction
if "auction_started" not in st.session_state:
    st.session_state.auction_started = False

if not st.session_state.auction_started:
    st.subheader("1. 경매 내전 설정")
    
    st.markdown("#### 진행자 지정")
    host_mode = st.radio("진행자 입력 방식", ["회원 선택", "직접 입력"], horizontal=True)
    if host_mode == "회원 선택":
        host_id = st.selectbox("진행자 (회원)", options=[u[1] for u in user_options], format_func=lambda x: user_dict[x][0].split('#')[0])
        host_name = user_dict[host_id][0].split('#')[0]
    else:
        host_name = st.text_input("진행자 (직접 입력)")
    
    with st.form("auction_setup"):
        num_teams = st.selectbox("팀 구성 수", [4, 6])
        
        # Select team leaders
        st.markdown("#### 팀장 지정 (선수 중 선택)")
        leaders = []
        cols = st.columns(3)
        for i in range(num_teams):
            with cols[i % 3]:
                leader = st.selectbox(f"Team {i+1} 팀장", options=[None] + [u[1] for u in user_options], format_func=lambda x: "선택안함" if x is None else user_dict[x][0], key=f"leader_{i}")
                leaders.append(leader)
        # Select Participants (매물)
        st.markdown("#### 👤 경매 매물(일반 참가자) 선택")
        selected_participants = st.multiselect(
            "이번 경매에 참가할 선수들을 모두 선택해주세요. (팀장 제외)",
            options=[u[1] for u in user_options],
            format_func=lambda x: user_dict[x][0]
        )
                
        start_btn = st.form_submit_button("경매 시작")
        
        if start_btn:
            # Validations
            actual_leaders = [l for l in leaders if l is not None]
            if len(set(actual_leaders)) != len(actual_leaders):
                st.error("중복된 팀장이 있습니다.")
            elif not host_name:
                st.error("진행자를 지정해주세요.")
            elif not selected_participants:
                st.error("경매에 참여할 일반 참가자를 1명 이상 선택해주세요.")
            else:
                overlap = set(actual_leaders).intersection(set(selected_participants))
                if overlap:
                    overlap_names = [user_dict[uid][0].split('#')[0] for uid in overlap]
                    st.error(f"팀장과 일반 참가자가 중복되었습니다: {', '.join(overlap_names)}")
                else:
                    st.session_state.auction_started = True
                    st.session_state.host_name = host_name
                    st.session_state.num_teams = num_teams
                    
                    # Init teams: list of dicts. each team has 'id', 'name', 'points', 'members'
                    st.session_state.teams = []
                    for i in range(num_teams):
                        leader_id = leaders[i]
                        members = []
                        if leader_id is not None:
                            members.append({'user_id': leader_id, 'points_spent': 0, 'role': 'Leader'})
                            leader_info = user_dict[leader_id]
                            leader_name = leader_info[0].split('#')[0] # use riot_id
                        else:
                            leader_name = f"Team {i+1}"
                        
                        st.session_state.teams.append({
                            'id': i,
                            'name': f"{leader_name} 팀" if leader_id is not None else leader_name,
                            'points': 1000,
                            'members': members
                        })
                    
                    # Remaining pool
                    st.session_state.remaining_pool = selected_participants.copy()
                    st.session_state.skipped_pool = []
                    st.session_state.current_target = None
                    st.rerun()
else:
    # --- Auction In Progress ---
    st.subheader(f"경매 진행 중 (진행자: {st.session_state.host_name})")
    
    # Render Teams
    cols = st.columns(st.session_state.num_teams)
    for i, team in enumerate(st.session_state.teams):
        with cols[i]:
            st.markdown(f"### {team['name']}")
            st.markdown(f"**남은 포인트: {team['points']}**")
            for m in team['members']:
                name = user_dict[m['user_id']][0]
                st.write(f"- {name} ({m['points_spent']}p)")
                
    st.divider()
    
    # Auction Control
    col1, col2 = st.columns([1, 1])
    
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
            st.info(f"### 현재 대상: {t_user[0]}\n**클랜 티어**: {t_user[3]} | **주 포지션**: {t_user[4]} | **부 포지션**: {t_user[5]}")
            
            # Action: Skip
            if st.button("⏭️ 유찰 (다음 뽑기에서 제외)"):
                st.session_state.remaining_pool.remove(st.session_state.current_target)
                st.session_state.skipped_pool.append(st.session_state.current_target)
                st.session_state.current_target = None
                st.rerun()
                
    with col2:
        if st.session_state.current_target:
            st.markdown("### 낙찰 입력")
            with st.form("bid_form"):
                win_team_idx = st.selectbox("낙찰 팀", range(st.session_state.num_teams), format_func=lambda x: st.session_state.teams[x]['name'])
                bid_points = st.number_input("소모 포인트", min_value=0, max_value=1000, value=0, step=10)
                submit_bid = st.form_submit_button("낙찰 확정")
                
                if submit_bid:
                    if len(st.session_state.teams[win_team_idx]['members']) >= 5:
                        st.error("해당 팀은 이미 5명의 인원이 꽉 찼습니다. 다른 팀을 선택해주세요.")
                    elif st.session_state.teams[win_team_idx]['points'] < bid_points:
                        st.error("팀의 남은 포인트가 부족합니다.")
                    else:
                        st.session_state.teams[win_team_idx]['points'] -= bid_points
                        st.session_state.teams[win_team_idx]['members'].append({
                            'user_id': st.session_state.current_target,
                            'points_spent': bid_points,
                            'role': 'Member'
                        })
                        st.session_state.remaining_pool.remove(st.session_state.current_target)
                        st.session_state.current_target = None
                        st.rerun()
                        
    st.divider()
    
    # Skipped Pool Manual Allocation
    if st.session_state.skipped_pool:
        st.markdown("### 유찰자 수동 배정")
        for idx, skip_user_id in enumerate(st.session_state.skipped_pool):
            skip_user = user_dict[skip_user_id]
            cols_skip = st.columns([3, 2, 1])
            with cols_skip[0]:
                st.write(f"- {skip_user[0]}")
            with cols_skip[1]:
                available_teams = [t for t in st.session_state.teams if len(t['members']) < 5]
                if available_teams:
                    assign_team_idx = st.selectbox("팀 선택", range(len(available_teams)), format_func=lambda x: available_teams[x]['name'], key=f"skip_sel_{idx}", label_visibility="collapsed")
                else:
                    st.write("배정 가능 팀 없음")
            with cols_skip[2]:
                if available_teams:
                    if st.button("배정", key=f"skip_btn_{idx}"):
                        target_team = available_teams[assign_team_idx]
                        real_idx = st.session_state.teams.index(target_team)
                        st.session_state.teams[real_idx]['members'].append({
                            'user_id': skip_user_id,
                            'points_spent': 0, # 유찰자 수동 배정이므로 0포인트
                            'role': 'Member'
                        })
                        st.session_state.skipped_pool.remove(skip_user_id)
                        st.rerun()
                        
    st.divider()
    st.markdown("### 경매 종료 및 저장")
    with st.form("save_auction_form"):
        winning_team = st.selectbox("우승 팀 (이력 보관용)", ["아직 모름"] + [t['name'] for t in st.session_state.teams])
        save_btn = st.form_submit_button("경매 확정 및 DB 저장", type="primary")
        
        if save_btn:
            players_data = []
            for team in st.session_state.teams:
                for m in team['members']:
                    players_data.append((m['user_id'], team['name'], m['role'], m['points_spent']))
            
            database.add_match("AUCTION", st.session_state.host_name, winning_team, players_data)
            st.success("경매 내전 이력이 성공적으로 저장되었습니다!")
            # Reset state
            st.session_state.auction_started = False
            del st.session_state.host_name
            del st.session_state.num_teams
            del st.session_state.teams
            del st.session_state.remaining_pool
            del st.session_state.skipped_pool
            del st.session_state.current_target
