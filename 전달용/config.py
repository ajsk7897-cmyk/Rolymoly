"""
프로젝트 설정 중앙화
"""
import os
from dotenv import load_dotenv

# .env 파일 로드 (있는 경우)
load_dotenv()

# Google Sheets 설정
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID", "여기에_구글_스프레드시트_ID_입력")

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "여름 이미지")
TEMP_DIR = BASE_DIR

# 임시 저장 파일
TEMP_SAVE_NORMAL = os.path.join(TEMP_DIR, "temp_save_normal.json")
TEMP_SAVE_AUCTION = os.path.join(TEMP_DIR, "temp_save_auction.json")

# 토너먼트 데이터 파일
TOURNAMENTS_FILE = os.path.join(TEMP_DIR, "tournaments.json")

# 캐시 설정
CACHE_TTL = 60  # 초 단위

# 경매 내전 설정
AUCTION_DEFAULT_TEAMS = 4
AUCTION_TEAM_OPTIONS = [4, 6, 8]
AUCTION_DEFAULT_POINTS = 1000

# 내전 기본 설정
MIN_PLAYERS_REQUIRED = 10
DEFAULT_ROLES = ["TOP", "JG", "MID", "AD", "SUP"]

# 점수 배점표 (솔로랭크)
TIER_SCORE_MAP = {
    "Iron 4": 10, "Iron 3": 10, "Iron 2": 10, "Iron 1": 10,
    "Bronze 4": 20, "Bronze 3": 30, "Bronze 2": 40, "Bronze 1": 50,
    "Silver 4": 60, "Silver 3": 70, "Silver 2": 80, "Silver 1": 90,
    "Gold 4": 120, "Gold 3": 130, "Gold 2": 140, "Gold 1": 150,
    "Platinum 4": 200, "Platinum 3": 210, "Platinum 2": 220, "Platinum 1": 230,
    "Emerald 4": 280, "Emerald 3": 300, "Emerald 2": 320, "Emerald 1": 340,
    "Diamond 4": 390, "Diamond 3": 420, "Diamond 2": 450, "Diamond 1": 480,
    "Master": 550, "Grandmaster": 800, "Challenger": 1000
}

TIER_ORDER = [
    "Iron 4", "Iron 3", "Iron 2", "Iron 1",
    "Bronze 4", "Bronze 3", "Bronze 2", "Bronze 1",
    "Silver 4", "Silver 3", "Silver 2", "Silver 1",
    "Gold 4", "Gold 3", "Gold 2", "Gold 1",
    "Platinum 4", "Platinum 3", "Platinum 2", "Platinum 1",
    "Emerald 4", "Emerald 3", "Emerald 2", "Emerald 1",
    "Diamond 4", "Diamond 3", "Diamond 2", "Diamond 1",
    "Master", "Grandmaster", "Challenger"
]

# 경매 포인트 테이블
AUCTION_POINTS_TABLE = [
    (700, 690),
    (600, 790),
    (550, 840),
    (480, 910),
    (450, 940),
    (420, 970),
    (390, 1000),
    (340, 1050),
    (320, 1070),
    (300, 1090),
    (280, 1110),
    (230, 1160),
    (220, 1170),
    (210, 1180),
    (200, 1190),
    (150, 1240),
    (140, 1250),
    (130, 1260),
    (120, 1270),
    (90, 1300),
    (80, 1310),
    (70, 1320),
]

# 경매 기본 포인트 (70 미만)
AUCTION_DEFAULT_POINTS_VALUE = 1330

# 로깅 설정
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"