import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from utils.tier_fetcher import fetch_tier_data, TIER_SCORE_MAP, calculate_clan_tier

st.set_page_config(page_title="회원 관리", page_icon="👑", layout="wide")

st.title("👑 회원 관리 (관리자 전용)")

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.info("운영진 전용 메뉴입니다. 부여받은 운영진 닉네임과 공통 비밀번호를 입력해주세요.")
    admin_id_input = st.text_input("운영진 닉네임 (예: 팬더가서자#kr1)")
    password = st.text_input("관리자 공통 비밀번호", type="password")
    
    if st.button("로그인"):
        approved_users = database.get_all_approved_users()
        is_valid_admin = False
        for u in approved_users:
            if len(u) == 12:
                u_id, r_id, t_line, s_tier, f_tier, p_score, m_score, m_stars, is_admin, m_bonus, main_pos, sub_pos = u
            else:
                u_id, r_id, t_line, s_tier, f_tier, p_score, m_score, m_stars, is_admin, m_bonus = u
            if is_admin == 1:
                full_name = f"{r_id}#{t_line}".lower()
                if admin_id_input.strip().lower() == full_name:
                    is_valid_admin = True
                    break
                    
        if not is_valid_admin:
            st.error("입력하신 닉네임은 운영진으로 등록되어 있지 않거나 올바르지 않습니다.")
        elif password == database.get_admin_password():
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

if st.button("로그아웃"):
    st.session_state.admin_authenticated = False
    st.rerun()

st.divider()

st.subheader("📝 승인 대기자 리스트")
pending_users = database.get_pending_users()

if not pending_users:
    st.info("승인 대기 중인 사용자가 없습니다.")
else:
    for user in pending_users:
        user_id, riot_id, tag_line, birthdate = user
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        
        col1.write(f"**{riot_id}#{tag_line}**")
        col2.write(f"생년월일: {birthdate}")
        
        if col3.button("✅ 가입 승인", key=f"approve_{user_id}"):
            with st.spinner("OP.GG에서 티어 정보를 가져오는 중..."):
                solo_tier, flex_tier, power_score = fetch_tier_data(riot_id, tag_line)
                database.approve_user(user_id, solo_tier, flex_tier, power_score)
            st.success(f"승인 완료! (솔로랭크: {solo_tier}, 자유랭크: {flex_tier}, 파워스코어: {power_score})")
            st.rerun()
            
        if col4.button("❌ 거절", key=f"reject_{user_id}"):
            database.reject_user(user_id)
            st.warning("가입이 거절되었습니다.")
            st.rerun()

st.divider()

st.subheader("👥 기존 회원 리스트")

if st.button("🔄 회원 전체 티어 최신화"):
    progress_text = "회원 티어 정보를 갱신 중입니다..."
    my_bar = st.progress(0, text=progress_text)
    approved_users_for_update = database.get_all_approved_users()
    
    total = len(approved_users_for_update)
    for i, u in enumerate(approved_users_for_update):
        user_id = int(u[0])
        riot_id = u[1]
        tag_line = u[2]
        
        solo_tier, flex_tier, power_score = fetch_tier_data(riot_id, tag_line)
        database.update_user_tier_info(user_id, solo_tier, flex_tier, power_score)
        
        my_bar.progress((i + 1) / total, text=f"{progress_text} ({i+1}/{total})")
    
    my_bar.empty()
    st.success("모든 회원의 티어 정보가 최신화되었습니다.")
    st.rerun()

# Style expander header to be dark yellow
st.markdown("""
<style>
[data-testid="stExpander"] details summary {
    background-color: #DAA520 !important;
    color: white !important;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

# Score table expander
with st.expander("현재 점수 배점표 확인"):
    st.markdown("""
    **[ 솔로랭크 스코어 배점표 및 MMR 증감폭 ]**
    - 마스터: 550점 (100LP 이상: 600점, 200LP 이상: 700점) `(내전 결과 반영 +- 50점 / 100LP: +- 20점 / 200LP: +- 20점)`
    - 그랜드마스터: 800점 `(내전 결과 반영 +- 40점)`
    - 챌린저: 1000점 `(내전 결과 반영 +- 10점)`
    - 다이아몬드: 390점 ~ 480점 `(내전 결과 반영 +- 6점 ~ 14점)`
    - 에메랄드: 280점 ~ 340점 `(내전 결과 반영 +- 4점 ~ 10점)`
    - 플래티넘: 200점 ~ 230점 `(내전 결과 반영 +- 2점 ~ 10점)`
    - 골드: 120점 ~ 150점 `(내전 결과 반영 +- 2점 ~ 10점)`
    - 실버: 60점 ~ 90점 `(내전 결과 반영 +- 2점 ~ 6점)`
    - 브론즈: 20점 ~ 50점 `(내전 결과 반영 +- 2점 ~ 2점)`
    - 아이언: 10점 `(내전 결과 반영 +- 2점)`

    *(※ 내전 결과 반영(MMR) 점수는 `(한 단계 상위 티어 점수 - 현재 티어 점수) / 5`를 기준으로 계산되며 최소 1점이 보장됩니다. 단, 챌린저는 고정 10점입니다.)*

    **[ 자유랭크 선형(Linear) 누적 점수 ]**
    - 아이언 4 (1점)부터 시작하여 한 단계(서브 티어) 올라갈 때마다 정확히 +1점씩 선형 누적. (예: 브론즈 4 = 5점)
    """)

approved_users = database.get_all_approved_users()
search_query = st.selectbox("🔍 회원 이름 검색", options=["전체"] + [f"{u[1]}#{u[2]}" for u in approved_users]) if approved_users else "전체"

user_stats = database.get_user_stats()

if not approved_users:
    st.info("등록된 회원이 없습니다.")
else:
    data = []
    for user in approved_users:
        if len(user) == 12:
            user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus, main_pos, sub_pos = user
        else:
            user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus = user
            main_pos, sub_pos = "", ""
            
        full_id = f"{riot_id}#{tag_line}"
        if search_query != "전체" and search_query != full_id:
            continue
            
        final_score = (manual_score if manual_score != -1 else power_score) + match_bonus
        clan_tier = calculate_clan_tier(final_score)
        
        stats = user_stats.get(user_id, {'total': 0, 'wins': 0, 'win_rate': 0})
        
        data.append({
            '아이디': user_id,
            '닉네임': riot_id,
            '태그라인': tag_line,
            '클랜 티어': clan_tier,
            '주 포지션': main_pos,
            '부 포지션': sub_pos,
            '내전 참가 판수': stats['total'],
            '내전 승률(%)': stats['win_rate'],
            '솔로랭크': solo_tier,
            '자유랭크': flex_tier,
            '기본 파워스코어': power_score,
            '수기 점수': manual_score,
            '수기 별(우승)': manual_stars,
            '운영진 여부': is_admin,
            '내전 보너스(MMR)': match_bonus,
            '최종 파워스코어': final_score
        })
        
    df = pd.DataFrame(data)
    if df.empty:
        st.warning("검색 결과가 없습니다.")
    else:
        st.dataframe(df, use_container_width=True)
    
    st.write("### 회원 관리 조작")
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    with col1:
        st.write("#### 파워스코어 수기 수정 (티어 기반)")
        target_id_score = st.selectbox("회원 선택 (수정)", df['아이디'].astype(str) + " - " + df['닉네임'].astype(str) + "#" + df['태그라인'].astype(str), key="score_select")
        
        tier_options = ["자동계산 (-1)"] + list(TIER_SCORE_MAP.keys()) + ["직접입력"]
        selected_tier = st.selectbox("적용할 솔랭 티어 선택", tier_options)
        
        if selected_tier == "자동계산 (-1)":
            new_score = -1
        elif selected_tier == "직접입력":
            new_score = st.number_input("점수 직접입력", min_value=-1, step=1, value=0)
        else:
            new_score = TIER_SCORE_MAP[selected_tier]
            
        if st.button("수정 적용", key="btn_score"):
            user_id = int(target_id_score.split(" - ")[0])
            database.update_manual_score(user_id, new_score)
            st.success(f"수정되었습니다. (반영 점수: {new_score})")
            st.rerun()
            
    with col2:
        st.write("#### 수기 별(⭐) 부여")
        target_id_star = st.selectbox("회원 선택 (별 추가)", df['아이디'].astype(str) + " - " + df['닉네임'].astype(str) + "#" + df['태그라인'].astype(str), key="star_select")
        new_stars = st.number_input("수기 별 개수 (기본 0)", value=0, min_value=0, step=1)
        if st.button("별 적용", key="btn_star"):
            user_id = int(target_id_star.split(" - ")[0])
            database.update_manual_stars(user_id, new_stars)
            st.success("별이 부여되었습니다.")
            st.rerun()
            
    with col3:
        st.write("#### 강제 탈퇴")
        target_id_kick = st.selectbox("회원 선택 (강퇴)", df['아이디'].astype(str) + " - " + df['닉네임'].astype(str) + "#" + df['태그라인'].astype(str), key="kick_select")
        if st.button("강제 탈퇴", type="primary", key="btn_kick"):
            user_id = int(target_id_kick.split(" - ")[0])
            database.kick_user(user_id)
            st.warning("탈퇴 처리되었습니다.")
            st.rerun()

    with col4:
        st.write("#### 🛡️ 운영진 권한 설정")
        target_id_admin = st.selectbox("회원 선택 (권한 변경)", df['아이디'].astype(str) + " - " + df['닉네임'].astype(str) + "#" + df['태그라인'].astype(str), key="admin_select")
        
        # 기본값을 현재 권한으로 세팅하기 위해 찾기
        current_user_id = int(target_id_admin.split(" - ")[0])
        current_admin_status = int(df[df['아이디'] == current_user_id]['운영진 여부'].values[0])
        
        admin_action = st.radio("권한 등급", ["일반 회원", "운영진 (관리자)"], index=current_admin_status)
        if st.button("권한 적용", key="btn_admin"):
            val = 1 if admin_action == "운영진 (관리자)" else 0
            database.update_admin_role(current_user_id, val)
            st.success("권한이 변경되었습니다.")
            st.rerun()

    st.markdown("---")
    st.write("#### 📝 포지션 정보 수정")
    target_id_pos = st.selectbox("회원 선택 (포지션 수정)", df['아이디'].astype(str) + " - " + df['닉네임'].astype(str) + "#" + df['태그라인'].astype(str), key="pos_select")
    
    current_user_id_pos = int(target_id_pos.split(" - ")[0])
    current_main_pos = df[df['아이디'] == current_user_id_pos]['주 포지션'].values[0]
    current_sub_pos = df[df['아이디'] == current_user_id_pos]['부 포지션'].values[0]
    
    positions_list = ["탑", "정글", "미드", "원딜", "서폿", ""]
    
    try:
        main_index = positions_list.index(current_main_pos)
    except ValueError:
        main_index = 0
        
    try:
        sub_index = positions_list.index(current_sub_pos)
    except ValueError:
        sub_index = 0

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        new_main_pos = st.selectbox("주 포지션 (수정)", positions_list, index=main_index)
    with col_p2:
        new_sub_pos = st.selectbox("부 포지션 (수정)", positions_list, index=sub_index)
        
    if st.button("포지션 적용", key="btn_pos"):
        database.update_user_positions(current_user_id_pos, new_main_pos, new_sub_pos)
        st.success("포지션이 성공적으로 변경되었습니다.")
        st.rerun()

st.divider()

st.subheader("🗑️ 개별 내전 이력 삭제")
matches = database.get_matches()
if matches:
    match_options = [f"{m[0]} - [{m[1]}] {m[3].split(' ')[0]} (진행자: {m[2]})" for m in matches]
    target_match = st.selectbox("삭제할 내전 선택", match_options)
    
    if st.button("해당 내전 삭제", type="primary"):
        match_id_to_delete = int(target_match.split(" - ")[0])
        database.delete_match(match_id_to_delete)
        st.success(f"{match_id_to_delete}번 내전이 삭제되었습니다. (관련 파워스코어 증감도 롤백되었습니다.)")
        st.rerun()
else:
    st.info("삭제할 내전 이력이 없습니다.")


st.divider()

st.subheader("⚠️ 내전 이력 초기화 (Danger Zone)")
st.warning("모든 내전 이력이 영구적으로 삭제됩니다. 복구할 수 없습니다.")

if "delete_confirm" not in st.session_state:
    st.session_state.delete_confirm = False

if not st.session_state.delete_confirm:
    if st.button("내전 이력 초기화 (Delete All)"):
        st.session_state.delete_confirm = True
        st.rerun()
else:
    st.error("정말 삭제하시겠습니까?")
    col1, col2 = st.columns(2)
    if col1.button("네, 모두 삭제합니다", type="primary"):
        database.delete_all_history()
        st.session_state.delete_confirm = False
        st.success("모든 내전 이력이 삭제되었습니다.")
        st.rerun()
    if col2.button("취소"):
        st.session_state.delete_confirm = False
        st.rerun()

st.divider()

st.subheader("⚙️ 관리자 설정")
with st.form("change_password_form"):
    new_pwd = st.text_input("새 관리자 비밀번호", type="password")
    new_pwd_confirm = st.text_input("새 관리자 비밀번호 확인", type="password")
    
    if st.form_submit_button("비밀번호 변경"):
        if not new_pwd:
            st.error("비밀번호를 입력하세요.")
        elif new_pwd != new_pwd_confirm:
            st.error("비밀번호가 일치하지 않습니다.")
        else:
            database.set_admin_password(new_pwd)
            st.success("비밀번호가 성공적으로 변경되었습니다!")
