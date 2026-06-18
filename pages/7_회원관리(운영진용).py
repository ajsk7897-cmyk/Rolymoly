import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from utils.tier_fetcher import fetch_tier_data

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
            u_id, r_id, t_line, s_tier, f_tier, p_score, m_score, m_stars, is_admin = u
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
approved_users = database.get_all_approved_users()

if not approved_users:
    st.info("등록된 회원이 없습니다.")
else:
    df = pd.DataFrame(approved_users, columns=['ID', 'Riot ID', 'Tag Line', '솔로랭크', '자유랭크', 'Power Score', 'Manual Score', 'Manual Stars', 'is_admin'])
    df['Final Score'] = df.apply(lambda row: row['Manual Score'] if row['Manual Score'] != -1 else row['Power Score'], axis=1)
    
    st.dataframe(df, use_container_width=True)
    
    st.write("### 회원 관리 조작")
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    with col1:
        st.write("#### 파워스코어 수기 수정")
        target_id_score = st.selectbox("회원 선택 (수정)", df['ID'].astype(str) + " - " + df['Riot ID'] + "#" + df['Tag Line'], key="score_select")
        new_score = st.number_input("새로운 점수 (-1: 자동계산)", value=-1, step=1)
        if st.button("수정 적용", key="btn_score"):
            user_id = int(target_id_score.split(" - ")[0])
            database.update_manual_score(user_id, new_score)
            st.success("수정되었습니다.")
            st.rerun()
            
    with col2:
        st.write("#### 수기 별(⭐) 부여")
        target_id_star = st.selectbox("회원 선택 (별 추가)", df['ID'].astype(str) + " - " + df['Riot ID'] + "#" + df['Tag Line'], key="star_select")
        new_stars = st.number_input("수기 별 개수 (기본 0)", value=0, min_value=0, step=1)
        if st.button("별 적용", key="btn_star"):
            user_id = int(target_id_star.split(" - ")[0])
            database.update_manual_stars(user_id, new_stars)
            st.success("별이 부여되었습니다.")
            st.rerun()
            
    with col3:
        st.write("#### 강제 탈퇴")
        target_id_kick = st.selectbox("회원 선택 (강퇴)", df['ID'].astype(str) + " - " + df['Riot ID'] + "#" + df['Tag Line'], key="kick_select")
        if st.button("강제 탈퇴", type="primary", key="btn_kick"):
            user_id = int(target_id_kick.split(" - ")[0])
            database.kick_user(user_id)
            st.warning("탈퇴 처리되었습니다.")
            st.rerun()

    with col4:
        st.write("#### 🛡️ 운영진 권한 설정")
        target_id_admin = st.selectbox("회원 선택 (권한 변경)", df['ID'].astype(str) + " - " + df['Riot ID'] + "#" + df['Tag Line'], key="admin_select")
        
        # 기본값을 현재 권한으로 세팅하기 위해 찾기
        current_user_id = int(target_id_admin.split(" - ")[0])
        current_admin_status = df[df['ID'] == current_user_id]['is_admin'].values[0]
        
        admin_action = st.radio("권한 등급", ["일반 회원", "운영진 (관리자)"], index=current_admin_status)
        if st.button("권한 적용", key="btn_admin"):
            val = 1 if admin_action == "운영진 (관리자)" else 0
            database.update_admin_role(current_user_id, val)
            st.success("권한이 변경되었습니다.")
            st.rerun()

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
