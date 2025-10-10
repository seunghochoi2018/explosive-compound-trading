#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 텔레그램 알림 봇 - 통합 실행 파일
- 데이터 수집, 모델 학습, 봇 실행을 하나로 통합
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
    from nvdl_nvdq_data_collector import NVDLNVDQDataCollector
    from nvdl_nvdq_trading_model import NVDLNVDQTradingModel
    from position_analysis_reporter import PositionAnalysisReporter
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    print(f"❌ 모듈 임포트 오류: {e}")
    print("필요한 Python 패키지를 설치해주세요:")
    print("pip install requests pandas numpy scikit-learn matplotlib seaborn")
    sys.exit(1)

def print_banner():
    """시작 배너 출력"""
    print("=" * 70)
    print("🤖 NVDL/NVDQ 텔레그램 알림 봇 (통합 버전)")
    print("📊 AI 기반 레버리지 ETF 거래 시스템")
    print("💬 실시간 텔레그램 알림")
    print("=" * 70)
    print("📈 NVDL: 3x 레버리지 NVIDIA ETF (상승 시 수익)")
    print("📉 NVDQ: 2x 역 레버리지 NASDAQ ETF (하락 시 수익)")
    print("⚡ 데이터 수집 → 모델 학습 → 봇 실행 자동화")
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
        print(f"❌ 누락된 패키지: {', '.join(missing_packages)}")
        print("다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True

def validate_api_key(api_key: str) -> bool:
    """FMP API 키 유효성 검증"""
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("❌ FMP API 키가 설정되지 않았습니다!")
        print("https://financialmodelingprep.com/developer/docs 에서 API 키를 발급받으세요.")
        return False

    # 간단한 테스트 요청
    import requests
    try:
        url = "https://financialmodelingprep.com/api/v3/quote/AAPL"
        response = requests.get(url, params={'apikey': api_key}, timeout=10)
        if response.status_code == 200:
            print("✅ FMP API 키 검증 성공")
            return True
        else:
            print(f"❌ FMP API 키 검증 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 키 검증 오류: {e}")
        return False

def test_telegram_connection() -> bool:
    """텔레그램 연결 테스트"""
    print("📱 텔레그램 연결 테스트 중...")

    try:
        telegram = TelegramNotifier()
        if telegram.test_connection():
            print("✅ 텔레그램 연결 성공")
            return True
        else:
            print("❌ 텔레그램 연결 실패")
            return False
    except Exception as e:
        print(f"❌ 텔레그램 연결 오류: {e}")
        return False

def run_integrated_system(api_key: str, auto_trading: bool = False):
    """통합 시스템 실행 (데이터 수집 + 모델 학습 + 봇 실행)"""
    print(f"\n🚀 통합 시스템 시작 (자동매매: {'ON' if auto_trading else 'OFF'})")

    # 사전 검증
    print("\n🔍 시스템 검증 중...")
    if not validate_api_key(api_key):
        return

    if not test_telegram_connection():
        return

    # 1단계: 데이터 수집 및 준비
    print("\n" + "="*50)
    print("📊 1단계: 데이터 수집 및 준비")
    print("="*50)

    collector = NVDLNVDQDataCollector(api_key)

    # 기존 데이터 확인 및 로드
    if not collector.load_data():
        print("🔄 기존 데이터가 없습니다. 전체 데이터를 새로 수집합니다...")
        print("⏰ 예상 소요 시간: 2-5분")

        collector.collect_all_data()
        collector.calculate_all_features()
        collector.save_data()

        print("✅ 데이터 수집 완료!")
    else:
        print("📁 기존 데이터를 로드했습니다.")

        # 최신 실시간 데이터로 업데이트
        print("🔄 최신 실시간 데이터로 업데이트 중...")
        for symbol in ['NVDL', 'NVDQ']:
            realtime_data = collector.fetch_realtime_data(symbol)
            if realtime_data:
                collector.realtime_data[symbol] = realtime_data
                print(f"  📈 {symbol}: ${realtime_data.get('price', 'N/A')}")

        collector.save_data()
        print("✅ 데이터 업데이트 완료!")

    # 데이터 요약 출력
    collector.print_summary()

    # 2단계: AI 모델 학습
    print("\n" + "="*50)
    print("🧠 2단계: AI 모델 학습")
    print("="*50)

    model = NVDLNVDQTradingModel(api_key)

    if not model.mass_learning():
        print("❌ 모델 학습 실패. 시스템을 종료합니다.")
        print("💡 해결 방법:")
        print("  1. 데이터가 충분한지 확인")
        print("  2. 인터넷 연결 상태 확인")
        print("  3. API 키가 유효한지 확인")
        return

    print("✅ AI 모델 학습 완료!")

    # 모델 성능 테스트
    print("\n🧪 모델 테스트 중...")
    action, symbol, confidence = model.get_portfolio_signal()
    print(f"📊 현재 AI 추천: {action} {symbol} (신뢰도: {confidence:.1%})")

    # 3단계: 텔레그램 봇 시작
    print("\n" + "="*50)
    print("🤖 3단계: 텔레그램 봇 시작")
    print("="*50)

    # 시작 알림 전송
    telegram = TelegramNotifier()
    start_message = f"""
🚀 **NVDL/NVDQ 봇 시작**

⚡ **모드**: {'자동매매' if auto_trading else '알림 전용'}
📊 **모델 상태**: 학습 완료
🎯 **현재 추천**: {action} {symbol}
📈 **신뢰도**: {confidence:.1%}

⏰ **시작 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔔 포지션 변경 시 실시간 알림을 보내드립니다!
    """.strip()

    telegram.send_message(start_message)

    print("📱 시작 알림을 텔레그램으로 전송했습니다.")
    print("🔄 5분마다 신호를 체크하고 변경 시 알림을 보냅니다.")
    print("⏹️ 중단하려면 Ctrl+C를 누르세요.")

    # 봇 실행
    bot = NVDLNVDQTelegramBot(api_key, auto_trading=auto_trading)

    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의한 중단")

        # 종료 알림
        telegram.send_message("⏹️ **봇 중단**\n\n시스템이 안전하게 종료되었습니다.")

    except Exception as e:
        print(f"\n❌ 봇 실행 오류: {e}")

        # 오류 알림
        telegram.notify_error("봇 실행 오류", str(e), "시스템을 재시작해주세요.")

def run_analysis_only(api_key: str):
    """분석 보고서만 생성"""
    print("\n📊 분석 보고서 모드")

    reporter = PositionAnalysisReporter(api_key)
    reporter.send_analysis_report()

    print("✅ 분석 보고서 전송 완료!")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="NVDL/NVDQ 텔레그램 알림 봇 (통합 버전)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 사용 예시:
  python main_integrated.py                # 통합 시스템 실행 (권장)
  python main_integrated.py --auto-trading # 자동매매 모드
  python main_integrated.py --analysis     # 분석 보고서만 생성

📝 기본 실행 시 다음이 자동으로 수행됩니다:
  1. 📊 NVDL/NVDQ 데이터 수집 (또는 기존 데이터 로드)
  2. 🧠 AI 모델 학습 (또는 기존 모델 로드)
  3. 🤖 텔레그램 봇 실행 (실시간 알림)
        """
    )

    parser.add_argument('--api-key', type=str,
                      default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                      help='FMP API 키')

    parser.add_argument('--auto-trading', action='store_true',
                      help='자동매매 모드 활성화 (기본: 알림만)')

    parser.add_argument('--analysis', action='store_true',
                      help='분석 보고서만 생성')

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
        if args.analysis:
            # 분석 보고서만 생성
            run_analysis_only(args.api_key)
        else:
            # 통합 시스템 실행
            run_integrated_system(args.api_key, args.auto_trading)

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의한 중단")
    except Exception as e:
        print(f"\n❌ 실행 오류: {e}")
        print("\n💡 문제 해결:")
        print("  1. 인터넷 연결 확인")
        print("  2. API 키 유효성 확인")
        print("  3. 필요한 패키지 설치 확인")
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n⏰ 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 실행 시간: {duration}")
        print("\n🙏 이용해 주셔서 감사합니다!")

if __name__ == "__main__":
    main()