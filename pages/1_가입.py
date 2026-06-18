import streamlit as st
import sys
import os
from datetime import datetime

# Add parent directory to sys.path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

st.set_page_config(page_title="일반회원 가입", page_icon="📝")

st.title("📝 일반회원 가입")

st.markdown("클랜 가입을 위해 롤 아이디와 생년월일을 입력해주세요.")

with st.form("join_form"):
    riot_id_full = st.text_input("롤 아이디 (예: Hide on bush#KR1)", placeholder="닉네임#태그라인 형식으로 입력해주세요")
    birthdate = st.date_input("생년월일", min_value=datetime(1950, 1, 1).date())
    
    submit = st.form_submit_button("가입 요청")
    
    if submit:
        if "#" not in riot_id_full:
            st.error("닉네임과 태그라인 사이에 '#'을 포함하여 정확히 입력해주세요.")
        else:
            riot_id, tag_line = riot_id_full.split("#", 1)
            riot_id = riot_id.strip()
            tag_line = tag_line.strip()
            
            if not riot_id or not tag_line:
                st.error("닉네임과 태그라인을 모두 입력해주세요.")
            else:
                database.add_user(riot_id, tag_line, birthdate.strftime("%Y-%m-%d"))
                st.success(f"{riot_id_full} 님의 가입 요청이 성공적으로 접수되었습니다! 관리자 승인 대기 중입니다.")
