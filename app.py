import streamlit as st
from utils.ui import set_background

st.set_page_config(
    page_title="롤 클랜 관리 및 내전 시스템",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)
set_background("190aa82672754bd77.gif")

st.title("⚔️ 롤 클랜 관리 및 내전 시스템 (V2 업데이트 됨)")

st.markdown("""
### 환영합니다!
왼쪽 사이드바에서 메뉴를 선택하여 이동해주세요.

- **가입**: 신규 클랜원 가입 요청
- **회원관리**: [관리자 전용] 회원 가입 승인 및 관리
- **회원리스트**: 클랜원 전체 목록 및 파워스코어 확인
- **일반내전**: 10인 밸런스 내전 팀 짜기
- **경매내전**: 포인트 기반 경매 내전 진행
- **내전이력**: 지난 내전 결과 확인
""")
