#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 텔레그램 알림 봇 - 메인 실행 파일
- 텔레그램을 통한 실시간 거래 신호 알림
- NVDL(3x 레버리지 NVIDIA ETF Long), NVDQ(2x 역 레버리지 NASDAQ ETF Short)
- 자동매매 지원 (선택사항)
"""

import sys
import os
import argparse
from datetime import datetime

# 필요한 모듈 임포트
try:
    from nvdl_nvdq_telegram_bot import NVDLNVDQTelegramBot
    from position_analysis_reporter import PositionAnalysisReporter
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    print(f" 모듈 임포트 오류: {e}")
    print("필요한 Python 패키지를 설치해주세요:")
    print("pip install requests pandas numpy scikit-learn matplotlib seaborn")
    sys.exit(1)

def print_banner():
    """시작 배너 출력"""
    print("=" * 70)
    print(" NVDL/NVDQ 텔레그램 알림 봇")
    print(" AI 기반 레버리지 ETF 거래 시스템")
    print("💬 실시간 텔레그램 알림")
    print("=" * 70)
    print(" NVDL: 3x 레버리지 NVIDIA ETF (상승 시 수익)")
    print(" NVDQ: 2x 역 레버리지 NASDAQ ETF (하락 시 수익)")
    print(" FMP API + 머신러닝 앙상블 모델")
    print("=" * 70)

def check_dependencies():
    """필요한 의존성 확인"""
    required_packages = [
        'requests', 'pandas', 'numpy', 'sklearn', 'matplotlib', 'seaborn'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f" 누락된 패키지: {', '.join(missing_packages)}")
        print("다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True

def validate_api_key(api_key: str) -> bool:
    """FMP API 키 유효성 검증"""
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print(" FMP API 키가 설정되지 않았습니다!")
        print("https://financialmodelingprep.com/developer/docs 에서 API 키를 발급받으세요.")
        return False

    # 간단한 테스트 요청
    import requests
    try:
        url = "https://financialmodelingprep.com/api/v3/quote/AAPL"
        response = requests.get(url, params={'apikey': api_key}, timeout=10)
        if response.status_code == 200:
            print(" FMP API 키 검증 성공")
            return True
        else:
            print(f" FMP API 키 검증 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f" API 키 검증 오류: {e}")
        return False

def test_telegram_connection() -> bool:
    """텔레그램 연결 테스트"""
    print(" 텔레그램 연결 테스트 중...")

    try:
        telegram = TelegramNotifier()
        if telegram.test_connection():
            print(" 텔레그램 연결 성공")
            return True
        else:
            print(" 텔레그램 연결 실패")
            return False
    except Exception as e:
        print(f" 텔레그램 연결 오류: {e}")
        return False

def run_data_collection(api_key: str):
    """데이터 수집 실행"""
    print("\n 데이터 수집 모드")

    from nvdl_nvdq_data_collector import NVDLNVDQDataCollector

    collector = NVDLNVDQDataCollector(api_key)

    # 기존 데이터 확인
    if collector.load_data():
        print("기존 데이터를 발견했습니다.")
        choice = input("새로 수집하시겠습니까? (y/N): ").lower()
        if choice != 'y':
            print("데이터 수집을 건너뜁니다.")
            return

    # 데이터 수집 실행
    collector.collect_all_data()
    collector.calculate_all_features()
    collector.save_data()
    collector.print_summary()

    print(" 데이터 수집 완료!")

def run_model_training(api_key: str):
    """모델 학습 실행"""
    print("\n 모델 학습 모드")

    from nvdl_nvdq_trading_model import NVDLNVDQTradingModel

    model = NVDLNVDQTradingModel(api_key)

    # 데이터 로드
    if not model.data_collector.load_data():
        print("데이터가 없습니다. 먼저 데이터를 수집하세요.")
        print("python main.py --collect-data")
        return

    # 모델 학습
    if model.mass_learning():
        print(" 모델 학습 완료!")

        # 테스트 신호 생성
        print("\n🧪 신호 테스트:")
        action, symbol, confidence = model.get_portfolio_signal()
        print(f"현재 추천: {action} {symbol} (신뢰도: {confidence:.2f})")

    else:
        print(" 모델 학습 실패!")

def run_analysis_report(api_key: str):
    """분석 보고서 생성"""
    print("\n 분석 보고서 모드")

    reporter = PositionAnalysisReporter(api_key)
    reporter.send_analysis_report()

    print(" 분석 보고서 전송 완료!")

def run_telegram_bot(api_key: str, auto_trading: bool = False):
    """텔레그램 봇 실행"""
    print(f"\n 텔레그램 봇 모드 (자동매매: {'ON' if auto_trading else 'OFF'})")

    # 사전 검증
    if not validate_api_key(api_key):
        return

    if not test_telegram_connection():
        return

    # 봇 생성 및 실행
    bot = NVDLNVDQTelegramBot(api_key, auto_trading=auto_trading)

    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의한 중단")
    except Exception as e:
        print(f"\n 봇 실행 오류: {e}")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="NVDL/NVDQ 텔레그램 알림 봇",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py                     # 텔레그램 봇 실행 (알림 모드)
  python main.py --auto-trading      # 텔레그램 봇 실행 (자동매매 모드)
  python main.py --collect-data      # 데이터 수집만 실행
  python main.py --train-model       # 모델 학습만 실행
  python main.py --analysis-report   # 분석 보고서 생성
  python main.py --test              # 연결 테스트만 실행
        """
    )

    parser.add_argument('--api-key', type=str,
                      default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                      help='FMP API 키')

    parser.add_argument('--auto-trading', action='store_true',
                      help='자동매매 모드 활성화 (기본: 알림만)')

    parser.add_argument('--collect-data', action='store_true',
                      help='데이터 수집만 실행')

    parser.add_argument('--train-model', action='store_true',
                      help='모델 학습만 실행')

    parser.add_argument('--analysis-report', action='store_true',
                      help='분석 보고서 생성 및 전송')

    parser.add_argument('--test', action='store_true',
                      help='연결 테스트만 실행')

    args = parser.parse_args()

    # 배너 출력
    print_banner()

    # 의존성 확인
    if not check_dependencies():
        return

    # 시작 시간 기록
    start_time = datetime.now()
    print(f"⏰ 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # 모드별 실행
        if args.test:
            # 연결 테스트
            validate_api_key(args.api_key)
            test_telegram_connection()

        elif args.collect_data:
            # 데이터 수집
            run_data_collection(args.api_key)

        elif args.train_model:
            # 모델 학습
            run_model_training(args.api_key)

        elif args.analysis_report:
            # 분석 보고서
            run_analysis_report(args.api_key)

        else:
            # 기본: 텔레그램 봇 실행
            run_telegram_bot(args.api_key, args.auto_trading)

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의한 중단")
    except Exception as e:
        print(f"\n 실행 오류: {e}")
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n⏰ 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 실행 시간: {duration}")

if __name__ == "__main__":
    main()