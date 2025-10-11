#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 완전 자동매매 시스템
- 24시간 자동 거래 + 실시간 학습
- 적응형 거래 주기 최적화
- 실제 API 연동 지원
- 텔레그램 실시간 알림
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 자체 모듈 임포트
from nvdl_nvdq_adaptive_auto_trader import (
    NVDLNVDQAdaptiveAutoTrader,
    AdaptiveFrequencyManager,
    MarketCondition,
    TradingState
)
from us_stock_api_manager import USStockAPIManager
from telegram_notifier import TelegramNotifier

class FullAutoTradingSystem:
    """완전 자동매매 시스템 (API 연동 포함)"""

    def __init__(self, fmp_api_key: str, broker_config: Dict, simulation_mode: bool = False):
        """
        완전 자동매매 시스템 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
            broker_config: 브로커 설정
            simulation_mode: 시뮬레이션 모드 여부
        """
        print("=" * 70)
        print(" NVDL/NVDQ 완전 자동매매 시스템")
        print(" 실제 API 연동 + 24시간 자동 거래")
        print(" 실시간 학습 + 적응형 최적화")
        print("=" * 70)

        self.fmp_api_key = fmp_api_key
        self.simulation_mode = simulation_mode
        self.running = False
        self.start_time = datetime.now()

        # 핵심 시스템 초기화
        self.adaptive_trader = NVDLNVDQAdaptiveAutoTrader(
            fmp_api_key, auto_trading=not simulation_mode
        )

        # 실제 브로커 API 연동
        if not simulation_mode:
            self.api_manager = USStockAPIManager(**broker_config)
        else:
            # 시뮬레이션 모드
            self.api_manager = USStockAPIManager(
                broker_type="mock",
                initial_balance=broker_config.get('initial_balance', 50000),
                position_size_usd=broker_config.get('position_size_usd', 2000)
            )

        self.telegram = TelegramNotifier()

        # 통합 상태 관리
        self.integrated_state = {
            'api_position': None,       # 실제 API 포지션
            'ai_position': None,        # AI 모델 추천 포지션
            'last_trade_time': None,    # 마지막 거래 시간
            'trade_sync_errors': 0,     # 동기화 오류 횟수
            'total_api_trades': 0,      # 실제 API 거래 횟수
            'api_profit': 0.0          # 실제 API 수익
        }

        # 안전 설정
        self.safety_config = {
            'max_daily_trades': 10,     # 일일 최대 거래 횟수
            'max_trade_frequency': 300, # 최소 거래 간격 (초)
            'emergency_stop_loss': 20,  # 긴급 손절 (%)
            'max_position_value': 10000, # 최대 포지션 가치 ($)
            'sync_check_interval': 300,  # 동기화 체크 간격 (초)
        }

        print(" 완전 자동매매 시스템 초기화 완료")

    def sync_positions(self) -> bool:
        """AI 모델과 실제 API 포지션 동기화"""
        try:
            # 실제 API 포지션 확인
            api_position = self.api_manager.get_current_position()
            ai_position = self.adaptive_trader.trading_state.position

            print(f"포지션 동기화 체크: API={api_position}, AI={ai_position}")

            # 동기화 상태 업데이트
            self.integrated_state['api_position'] = api_position
            self.integrated_state['ai_position'] = ai_position

            # 불일치 처리
            if api_position != ai_position:
                print(f" 포지션 불일치 감지!")

                if api_position and not ai_position:
                    # API에는 포지션이 있는데 AI는 없음 -> AI 상태 동기화
                    print(f"AI 상태를 API 포지션 {api_position}로 동기화")
                    self.adaptive_trader.trading_state.position = api_position
                    self.adaptive_trader.trading_state.entry_time = datetime.now()

                    # 진입가 추정 (실제로는 API에서 가져와야 함)
                    current_price = self.adaptive_trader.get_current_price(api_position)
                    self.adaptive_trader.trading_state.entry_price = current_price

                elif not api_position and ai_position:
                    # AI는 포지션이 있다고 생각하는데 API에는 없음 -> AI 상태 초기화
                    print(f"AI 상태 초기화 (실제 포지션 없음)")
                    self.adaptive_trader.trading_state.position = None
                    self.adaptive_trader.trading_state.entry_time = None
                    self.adaptive_trader.trading_state.entry_price = None

                elif api_position != ai_position:
                    # 서로 다른 포지션 -> 실제 포지션으로 통일
                    print(f"포지션 통일: API {api_position}로 맞춤")

                    # 기존 포지션 청산 (AI 쪽)
                    self.adaptive_trader.trading_state.position = None

                    # 새로운 포지션으로 설정
                    self.adaptive_trader.trading_state.position = api_position
                    self.adaptive_trader.trading_state.entry_time = datetime.now()
                    current_price = self.adaptive_trader.get_current_price(api_position)
                    self.adaptive_trader.trading_state.entry_price = current_price

                self.integrated_state['trade_sync_errors'] += 1

                # 텔레그램 알림
                self.telegram.send_message(
                    f" **포지션 동기화**\n\n"
                    f"API 포지션: {api_position}\n"
                    f"AI 포지션: {ai_position}\n"
                    f"→ {api_position or '없음'}로 동기화 완료"
                )

                return False

            return True

        except Exception as e:
            print(f"포지션 동기화 오류: {e}")
            self.telegram.notify_error("포지션 동기화 오류", str(e))
            return False

    def execute_real_trade(self, action: str, symbol: str, confidence: float) -> bool:
        """실제 거래 실행"""
        try:
            print(f"\n 실제 거래 실행: {action} {symbol}")

            # 안전 체크
            if not self.safety_check(action, symbol):
                return False

            if action == "ENTER":
                # 포지션 진입
                result = self.api_manager.open_position(symbol)

                if result.get('success'):
                    self.integrated_state['total_api_trades'] += 1
                    self.integrated_state['last_trade_time'] = datetime.now()

                    print(f" {symbol} 실제 포지션 진입 성공")

                    # 텔레그램 알림
                    self.telegram.send_message(
                        f" **실제 거래 실행**\n\n"
                        f" 종목: {symbol}\n"
                        f" 수량: {result.get('quantity')}주\n"
                        f" 가격: ${result.get('price', 0):.2f}\n"
                        f" 주문ID: {result.get('order_id')}\n"
                        f" 신뢰도: {confidence:.1%}"
                    )

                    return True
                else:
                    print(f" {symbol} 실제 포지션 진입 실패: {result.get('error')}")
                    self.telegram.notify_error(
                        f"{symbol} 포지션 진입 실패",
                        result.get('error', '알 수 없는 오류')
                    )
                    return False

            elif action == "EXIT":
                # 포지션 청산
                result = self.api_manager.close_position(symbol)

                if result.get('success'):
                    self.integrated_state['total_api_trades'] += 1
                    self.integrated_state['last_trade_time'] = datetime.now()

                    pnl = result.get('pnl', 0)
                    pnl_pct = result.get('pnl_pct', 0)
                    self.integrated_state['api_profit'] += pnl_pct

                    print(f" {symbol} 실제 포지션 청산 성공: {pnl_pct:+.2f}%")

                    # 텔레그램 알림
                    self.telegram.send_message(
                        f" **실제 거래 완료**\n\n"
                        f" 종목: {symbol}\n"
                        f" 수량: {result.get('quantity')}주\n"
                        f" 청산가: ${result.get('price', 0):.2f}\n"
                        f" 수익: {pnl_pct:+.2f}%\n"
                        f" 누적 수익: {self.integrated_state['api_profit']:+.2f}%\n"
                        f" 주문ID: {result.get('order_id')}"
                    )

                    return True
                else:
                    print(f" {symbol} 실제 포지션 청산 실패: {result.get('error')}")
                    self.telegram.notify_error(
                        f"{symbol} 포지션 청산 실패",
                        result.get('error', '알 수 없는 오류')
                    )
                    return False

        except Exception as e:
            print(f"실제 거래 실행 오류: {e}")
            self.telegram.notify_error("실제 거래 실행 오류", str(e))
            return False

    def safety_check(self, action: str, symbol: str) -> bool:
        """안전 체크"""
        try:
            # 일일 거래 횟수 체크
            if self.integrated_state['total_api_trades'] >= self.safety_config['max_daily_trades']:
                print(f" 일일 최대 거래 횟수 초과: {self.integrated_state['total_api_trades']}")
                return False

            # 거래 간격 체크
            if self.integrated_state['last_trade_time']:
                time_diff = (datetime.now() - self.integrated_state['last_trade_time']).total_seconds()
                if time_diff < self.safety_config['max_trade_frequency']:
                    print(f" 최소 거래 간격 미충족: {time_diff:.0f}초")
                    return False

            # 긴급 손절 체크
            if action == "ENTER":
                account_info = self.api_manager.get_account_summary()
                current_loss = 0

                for pos in account_info.get('positions', []):
                    if pos.get('unrealized_pnl_pct', 0) < 0:
                        current_loss += abs(pos['unrealized_pnl_pct'])

                if current_loss > self.safety_config['emergency_stop_loss']:
                    print(f" 긴급 손절 임계값 초과: {current_loss:.2f}%")
                    self.telegram.send_message(
                        f" **긴급 손절 작동**\n\n"
                        f"현재 손실: {current_loss:.2f}%\n"
                        f"임계값: {self.safety_config['emergency_stop_loss']}%\n"
                        f"새로운 포지션 진입 차단"
                    )
                    return False

            # 시장 개장 시간 체크 (옵션)
            if not self.api_manager.is_market_open():
                print(" 시장 비개장 시간")
                return False

            return True

        except Exception as e:
            print(f"안전 체크 오류: {e}")
            return False

    def enhanced_trading_cycle(self):
        """강화된 거래 사이클 (실제 API 연동)"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 강화된 거래 사이클 시작")

            # 1. 포지션 동기화 체크
            sync_success = self.sync_positions()
            if not sync_success:
                print("포지션 동기화 실패, 안전 모드로 전환")
                return

            # 2. AI 거래 사이클 실행 (시뮬레이션)
            self.adaptive_trader.trading_cycle()

            # 3. AI 결정을 실제 API로 실행
            ai_position = self.adaptive_trader.trading_state.position
            api_position = self.integrated_state['api_position']

            # AI가 새로운 포지션을 추천했을 때
            if ai_position != api_position:
                print(f"포지션 변경 신호: {api_position} → {ai_position}")

                # 기존 포지션 청산
                if api_position:
                    success = self.execute_real_trade("EXIT", api_position, 0.8)
                    if not success:
                        print("기존 포지션 청산 실패")
                        return

                # 새로운 포지션 진입
                if ai_position:
                    # AI 신뢰도 확인
                    _, _, confidence = self.adaptive_trader.trading_model.get_portfolio_signal()

                    if confidence > 0.5:  # 높은 신뢰도만 실제 거래
                        success = self.execute_real_trade("ENTER", ai_position, confidence)
                        if not success:
                            print("새로운 포지션 진입 실패")
                            return
                    else:
                        print(f"신뢰도 부족으로 실제 거래 건너뜀: {confidence:.2f}")

            # 4. 계좌 상태 업데이트
            self.update_account_status()

        except Exception as e:
            print(f"강화된 거래 사이클 오류: {e}")
            self.telegram.notify_error("강화된 거래 사이클 오류", str(e))

    def update_account_status(self):
        """계좌 상태 업데이트"""
        try:
            account_summary = self.api_manager.get_account_summary()

            # 현재 포지션 정보 출력
            positions = account_summary.get('positions', [])
            if positions:
                for pos in positions:
                    symbol = pos['symbol']
                    pnl_pct = pos['unrealized_pnl_pct']
                    print(f"실제 포지션: {symbol} | PnL: {pnl_pct:+.2f}%")
            else:
                print("실제 포지션: 없음")

        except Exception as e:
            print(f"계좌 상태 업데이트 오류: {e}")

    def run(self):
        """메인 실행 루프"""
        print("\n 완전 자동매매 시스템 시작")

        # 초기 시스템 로드
        self.adaptive_trader.load_state()

        # 데이터 준비
        print(" 데이터 및 모델 준비 중...")
        if not self.adaptive_trader.data_collector.load_data():
            self.adaptive_trader.data_collector.collect_all_data()
            self.adaptive_trader.data_collector.calculate_all_features()
            self.adaptive_trader.data_collector.save_data()

        if not self.adaptive_trader.trading_model.mass_learning():
            print(" 모델 학습 실패")
            return

        print(" 시스템 준비 완료!")

        # 초기 계좌 상태
        self.api_manager.print_account_status()

        # 시작 알림
        mode_text = "시뮬레이션" if self.simulation_mode else "실제 거래"
        start_message = f"""
 **완전 자동매매 시작**

 **모드**: {mode_text}
 **대상**: NVDL/NVDQ
 **AI 모델**: 학습 완료
 **거래 주기**: 적응형 최적화

⏰ **시작**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

 실시간 거래 알림을 보내드립니다!
        """.strip()

        self.telegram.send_message(start_message)

        self.running = True

        try:
            last_sync_check = datetime.now()
            last_daily_reset = datetime.now().date()
            last_status_update = datetime.now()

            while self.running:
                # 강화된 거래 사이클
                self.enhanced_trading_cycle()

                # 정기 동기화 체크
                if (datetime.now() - last_sync_check).total_seconds() >= self.safety_config['sync_check_interval']:
                    self.sync_positions()
                    last_sync_check = datetime.now()

                # 일일 카운터 리셋
                if datetime.now().date() > last_daily_reset:
                    self.integrated_state['total_api_trades'] = 0
                    last_daily_reset = datetime.now().date()

                    # 일일 요약 전송
                    self.send_daily_summary()

                # 상태 업데이트 (6시간마다)
                if (datetime.now() - last_status_update).total_seconds() >= 21600:
                    self.send_comprehensive_status()
                    last_status_update = datetime.now()

                # 적응형 학습
                self.adaptive_trader.adaptive_learning_cycle()

                # 상태 저장
                self.adaptive_trader.save_state()

                # 대기
                sleep_time = self.adaptive_trader.adaptive_config['base_check_interval']
                print(f"다음 체크까지 {sleep_time//60}분 대기...")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n⏹ 사용자에 의한 중단")
        except Exception as e:
            print(f"\n 시스템 오류: {e}")
            self.telegram.notify_error("자동매매 시스템 오류", str(e))
        finally:
            self.running = False
            self.cleanup()

    def send_daily_summary(self):
        """일일 요약 전송"""
        api_trades = self.integrated_state['total_api_trades']
        api_profit = self.integrated_state['api_profit']
        ai_trades = self.adaptive_trader.daily_trades
        ai_profit = self.adaptive_trader.daily_profit

        summary_message = f"""
 **일일 거래 요약**

 **날짜**: {datetime.now().strftime('%Y-%m-%d')}

 **실제 API 거래**:
- 거래 횟수: {api_trades}회
- 수익률: {api_profit:+.2f}%

 **AI 시뮬레이션**:
- 거래 횟수: {ai_trades}회
- 수익률: {ai_profit:+.2f}%

 **누적 성과**:
- 총 거래: {self.adaptive_trader.total_trades}회
- 승률: {self.adaptive_trader.get_win_rate():.1f}%
- 총 수익: {self.adaptive_trader.total_profit:+.2f}%

 **시스템 상태**: 정상 운영 중
        """.strip()

        self.telegram.send_message(summary_message)

    def send_comprehensive_status(self):
        """종합 상태 보고"""
        account_summary = self.api_manager.get_account_summary()
        account_info = account_summary.get('account_info', {})

        status_message = f"""
 **종합 상태 보고**

 **계좌 현황**:
- 총 자산: ${account_info.get('equity', 0):,.2f}
- 현금: ${account_info.get('cash', 0):,.2f}
- 포트폴리오: ${account_info.get('portfolio_value', 0):,.2f}

 **현재 포지션**: {self.integrated_state['api_position'] or '없음'}

 **성과 요약**:
- API 거래: {self.integrated_state['total_api_trades']}회
- API 수익: {self.integrated_state['api_profit']:+.2f}%
- 동기화 오류: {self.integrated_state['trade_sync_errors']}회

⏱ **가동 시간**: {datetime.now() - self.start_time}
 **최적 주기**: {self.adaptive_trader.frequency_manager.current_optimal_frequency}

 **상태**: 정상 운영 중
        """.strip()

        self.telegram.send_message(status_message)

    def cleanup(self):
        """정리 작업"""
        try:
            # 모든 포지션 청산 (선택적)
            positions = self.api_manager.get_positions()
            if positions:
                print(" 시스템 종료 시 포지션이 있습니다.")
                choice = input("모든 포지션을 청산하시겠습니까? (y/N): ").lower()
                if choice == 'y':
                    results = self.api_manager.close_all_positions()
                    print(f"포지션 청산 결과: {results}")

            # 최종 상태 저장
            self.adaptive_trader.save_state()

            # 종료 알림
            self.telegram.send_message(
                f"⏹ **완전 자동매매 종료**\n\n"
                f"실행 시간: {datetime.now() - self.start_time}\n"
                f"실제 거래: {self.integrated_state['total_api_trades']}회\n"
                f"최종 수익: {self.integrated_state['api_profit']:+.2f}%\n"
                f"시스템이 안전하게 종료되었습니다."
            )

            print(" 완전 자동매매 시스템 종료")

        except Exception as e:
            print(f"정리 작업 오류: {e}")

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="NVDL/NVDQ 완전 자동매매 시스템")
    parser.add_argument('--fmp-api-key', type=str,
                       default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                       help='FMP API 키')
    parser.add_argument('--simulation', action='store_true',
                       help='시뮬레이션 모드')
    parser.add_argument('--broker', type=str, default='mock',
                       choices=['mock', 'alpaca'],
                       help='브로커 선택')
    parser.add_argument('--initial-balance', type=float, default=50000,
                       help='초기 자금 (시뮬레이션 모드)')
    parser.add_argument('--position-size', type=float, default=2000,
                       help='포지션 크기 ($)')

    args = parser.parse_args()

    # 브로커 설정
    broker_config = {
        'broker_type': args.broker,
        'initial_balance': args.initial_balance,
        'position_size_usd': args.position_size
    }

    # Alpaca 설정 (실제 사용 시 설정 필요)
    if args.broker == 'alpaca':
        broker_config.update({
            'api_key': 'YOUR_ALPACA_API_KEY',
            'secret_key': 'YOUR_ALPACA_SECRET_KEY',
            'paper_trading': True  # 실거래 시 False로 변경
        })

    # 완전 자동매매 시스템 생성 및 실행
    trading_system = FullAutoTradingSystem(
        fmp_api_key=args.fmp_api_key,
        broker_config=broker_config,
        simulation_mode=args.simulation
    )

    trading_system.run()

if __name__ == "__main__":
    main()