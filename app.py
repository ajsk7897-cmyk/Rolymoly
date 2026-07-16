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
<style>
    /* -------------------------------------------------------------------------- */
    /* UI/UX 레이아웃 교정 (픽셀 매칭 및 줄바꿈 방지)                           */
    /* -------------------------------------------------------------------------- */
    
    /* 1. 절대 줄바꿈 금지 (No-Wrap 강제) */
    .stButton > button, 
    .stButton > button *,
    [data-baseweb="tab"], 
    [data-baseweb="tab"] *, 
    td, th, 
    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] *, 
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {
        white-space: nowrap !important;
        word-break: keep-all !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* 2. 입력창 및 버튼 규격(높이) 완벽 통일 */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input, 
    .stSelectbox > div > div > div[data-baseweb="select"],
    .stDateInput > div > div > input,
    .stButton > button {
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        line-height: 42px !important;
        margin: 0 !important;
        box-sizing: border-box !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* 3. 대시보드 메트릭 박스(KPI) 동일 높이화 */
    [data-testid="metric-container"] {
        min-height: 130px !important;
        height: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        overflow: hidden !important;
    }
    /* -------------------------------------------------------------------------- */
</style>
""", unsafe_allow_html=True)

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
