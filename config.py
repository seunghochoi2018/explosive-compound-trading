# NVDL/NVDQ 트레이더 설정 파일

# Financial Modeling Prep API 설정
# https://financialmodelingprep.com/developer/docs 에서 무료 API 키 발급
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"  # 기존 코드에서 사용 중인 API 키

# API 엔드포인트
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

# 거래 설정
INITIAL_BALANCE = 10000.0
SYMBOLS = ['NVDL', 'NVDQ']

# 시간대 설정 (EST)
MARKET_TIMEZONE = 'US/Eastern'
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# 거래 주기 설정
TRADING_INTERVALS = {
    '15m': 900,    # 15분
    '1h': 3600,    # 1시간
    '4h': 14400,   # 4시간
    '12h': 43200,  # 12시간
    '1d': 86400    # 1일
}

# 레버리지 옵션 (NVDL/NVDQ는 이미 레버리지 ETN이므로 현물만)
LEVERAGES = [1]  # 현물 거래만

# 거래 방향
DIRECTIONS = ['both', 'long_only', 'short_only']

# 전략 종류
STRATEGIES = ['momentum', 'counter_trend', 'breakout']

# 리스크 관리 (레버리지 ETN 특성상 더 보수적)
MAX_POSITION_SIZE = 0.05  # 최대 포지션 크기 (5%)
STOP_LOSS_THRESHOLD = -0.05  # 손절매 (-5%) - NVDL/NVDQ는 변동성이 크므로
TAKE_PROFIT_THRESHOLD = 0.02  # 익절 (2%) - 더 보수적으로

# 저장 설정
SAVE_INTERVAL = 600  # 10분마다 저장
STATUS_INTERVAL = 120  # 2분마다 상태 출력
WEIGHT_UPDATE_INTERVAL = 300  # 5분마다 가중치 업데이트

# 수렴 시스템 설정
CONVERGENCE_START_TRADES = 30  # 총 30회 거래 후 수렴 시작
TOP_MODEL_RATIO = 0.2  # 상위 20% 모델 선택

print("NVDL/NVDQ 트레이더 설정이 로드되었습니다.")
print(f"거래 종목: {', '.join(SYMBOLS)}")
print(f"초기 자본: ${INITIAL_BALANCE:,.0f}")
print(f"API 키: {'설정됨' if FMP_API_KEY != 'demo' else '데모 모드'}")