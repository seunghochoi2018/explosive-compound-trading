# Bybit API 설정 (실거래 모드)
# 중요: ETHUSD 거래용 설정 - ETHUSDT 아님!
BYBIT_CONFIG = {
    "api_key": "test_api_key",
    "api_secret": "test_api_secret",
    "trading_mode": "live",  # 실거래 모드
    "enable_real_trading": True,
}

TELEGRAM_CONFIG = {
    "token": "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U",
    "chat_id": "7805944420"
}

def get_trading_mode():
    return "live"

def get_api_credentials():
    # 실제 API 키 사용 - LIVE 모드 강제
    # 0.0011 ETH 잔고 확인된 계좌
    return {
        "api_key": "KLthPXAti9nWKLOeNX",
        "api_secret": "ioRLGkzvHcmOoJeJhBkDmG2JJPuSROOEVm2S",
        "testnet": False  # 실거래 모드!
    }