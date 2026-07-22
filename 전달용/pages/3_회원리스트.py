import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from utils.tier_fetcher import calculate_clan_tier, abbreviate_tier
from utils.helpers import unpack_user_data, calculate_user_scores, calculate_trophy_symbols_v2

from utils.ui import set_background
st.set_page_config(page_title="회원 리스트", page_icon="👥", layout="wide")
set_background("images (1).jpg")

st.title("👥 회원 리스트")

st.markdown("클랜에 가입된 모든 회원 목록입니다. 🌟(별표)는 경매 내전 우승 횟수를 의미합니다.")

# Fetch data
approved_users = database.get_all_approved_users()
auction_points, auction_cats = database.get_auction_points_by_user()

# Search functionality (Dropdown + Typing)
user_names = [f"{u[1]}#{u[2]}" for u in approved_users] if approved_users else []
search_query = st.selectbox("🔍 클랜원 닉네임 검색", options=["전체"] + user_names)

if not approved_users:
    st.info("아직 승인된 회원이 없습니다.")
else:
    data = []
    for user in approved_users:
        user_dict = unpack_user_data(user)
        
        full_id = f"{user_dict['riot_id']}#{user_dict['tag_line']}"
        
        if search_query != "전체" and search_query != full_id:
            continue
        
        # Calculate scores using helper
        base_score, final_score, clan_tier = calculate_user_scores(user_dict)
        
        # Calculate trophy symbols
        total_points = auction_points.get(user_dict['user_id'], 0) + user_dict['manual_stars']
        total_cats = auction_cats.get(user_dict['user_id'], 0)
        symbol_str = calculate_trophy_symbols_v2(total_points, total_cats)
        
        role_str = "👑 운영진" if user_dict['is_admin'] == 1 else "일반"
        
        data.append({
            "클랜 티어": clan_tier,
            "권한": role_str,
            "🌟 우승 기호": symbol_str,
            "롤 아이디": full_id,
            "주 포지션": user_dict['main_pos'],
            "부 포지션": user_dict['sub_pos'],
            "솔로랭크": abbreviate_tier(user_dict['solo_tier']),
            "자유랭크": abbreviate_tier(user_dict['flex_tier']),
            "최종 파워스코어": final_score
        })
        
    if not data:
        st.warning("검색 결과가 없습니다.")
    else:
        df = pd.DataFrame(data)
    
    # Sort by Power Score descending
    df = df.sort_values(by="최종 파워스코어", ascending=False).reset_index(drop=True)
    
    # Render table
    st.dataframe(df, use_container_width=True)
    
    # CSV Download
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 회원 리스트 CSV 다운로드",
        data=csv,
        file_name='member_list.csv',
        mime='text/csv',
    )
