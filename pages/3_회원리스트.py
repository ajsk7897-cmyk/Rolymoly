import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from utils.tier_fetcher import calculate_clan_tier, abbreviate_tier

st.set_page_config(page_title="회원 리스트", page_icon="👥", layout="wide")

st.title("👥 회원 리스트")

st.markdown("클랜에 가입된 모든 회원 목록입니다. 🌟(별표)는 경매 내전 우승 횟수를 의미합니다.")

# Fetch data
approved_users = database.get_all_approved_users()
auction_wins = database.get_auction_wins_by_user()

# Search functionality (Dropdown + Typing)
user_names = [f"{u[1]}#{u[2]}" for u in approved_users] if approved_users else []
search_query = st.selectbox("🔍 클랜원 닉네임 검색", options=["전체"] + user_names)



if not approved_users:
    st.info("아직 승인된 회원이 없습니다.")
else:
    data = []
    for user in approved_users:
        if len(user) == 12:
            user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus, main_pos, sub_pos = user
        else: # Fallback in case of old data structure
            user_id, riot_id, tag_line, solo_tier, flex_tier, power_score, manual_score, manual_stars, is_admin, match_bonus = user
            main_pos, sub_pos = "", ""
            
        full_id = f"{riot_id}#{tag_line}"
        
        if search_query != "전체" and search_query != full_id:
            continue
        
        # Calculate final score
        final_score = (manual_score if manual_score != -1 else power_score) + match_bonus
        
        # Calculate stars
        wins = auction_wins.get(user_id, 0) + manual_stars
        stars = "⭐" * wins if wins > 0 else "-"
        
        full_id = f"{riot_id}#{tag_line}"
        role_str = "👑 운영진" if is_admin == 1 else "일반"
        
        if match_bonus > 0:
            score_change_str = f"+{match_bonus}점"
        elif match_bonus < 0:
            score_change_str = f"{match_bonus}점"
        else:
            score_change_str = "0점"
        
        clan_tier = calculate_clan_tier(final_score)
        
        data.append({
            "클랜 티어": clan_tier,
            "권한": role_str,
            "🌟 우승 횟수": stars,
            "롤 아이디": full_id,
            "주 포지션": main_pos,
            "부 포지션": sub_pos,
            "솔로랭크": abbreviate_tier(solo_tier),
            "자유랭크": abbreviate_tier(flex_tier),
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
