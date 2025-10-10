#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 텔레그램 알림 봇
- 실시간 포지션 변경 알림
- 수익패턴 학습 및 신호 생성
- 자동매매 지원 (옵션)
- 텔레그램을 통한 모니터링
"""

import json
import time
import pickle
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 자체 모듈 임포트
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector
from nvdl_nvdq_trading_model import NVDLNVDQTradingModel
from telegram_notifier import TelegramNotifier

class NVDLNVDQTelegramBot:
    def __init__(self, fmp_api_key: str, auto_trading: bool = False):
        """
        NVDL/NVDQ 텔레그램 봇 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
            auto_trading: 자동매매 활성화 여부 (기본: False, 알림만)
        """
        print("=" * 60)
        print("🤖 NVDL/NVDQ 텔레그램 알림 봇")
        print("📊 레버리지 ETF 전용 AI 거래 시스템")
        print("💬 실시간 텔레그램 알림")
        print("=" * 60)

        # 기본 설정
        self.fmp_api_key = fmp_api_key
        self.auto_trading = auto_trading
        self.running = False
        self.start_time = datetime.now()

        # 컴포넌트 초기화
        print("\n📡 컴포넌트 초기화 중...")
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)
        self.trading_model = NVDLNVDQTradingModel(fmp_api_key)
        self.telegram = TelegramNotifier()

        # 포지션 관리
        self.current_position = None  # 'NVDL', 'NVDQ', None
        self.position_entry_time = None
        self.position_entry_price = None
        self.position_features = None

        # 신호 추적
        self.last_signal = "HOLD"
        self.last_signal_time = None
        self.signal_history = []

        # 성과 추적
        self.daily_trades = 0
        self.daily_profit = 0.0
        self.position_changes = []  # 포지션 변경 기록

        # 실행 설정
        self.config = {
            'check_interval': 300,      # 5분마다 체크
            'min_signal_confidence': 0.3,  # 최소 신뢰도
            'max_position_time': 24,    # 최대 포지션 보유 시간 (시간)
            'daily_summary_hour': 18,   # 일일 요약 시간 (18시)
            'status_update_interval': 3600,  # 상태 업데이트 간격 (1시간)
        }

        # 상태 파일
        self.state_file = "nvdl_nvdq_bot_state.json"

        print("✅ 컴포넌트 초기화 완료")

    def load_state(self):
        """봇 상태 로드"""
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                self.current_position = state.get('current_position')
                self.position_entry_time = state.get('position_entry_time')
                if self.position_entry_time:
                    self.position_entry_time = datetime.fromisoformat(self.position_entry_time)
                self.position_entry_price = state.get('position_entry_price')
                self.daily_trades = state.get('daily_trades', 0)
                self.daily_profit = state.get('daily_profit', 0.0)
                self.last_signal = state.get('last_signal', 'HOLD')
                print(f"상태 로드 완료: 포지션={self.current_position}, 일일거래={self.daily_trades}")
        except FileNotFoundError:
            print("상태 파일 없음. 새로 시작합니다.")
        except Exception as e:
            print(f"상태 로드 오류: {e}")

    def save_state(self):
        """봇 상태 저장"""
        try:
            state = {
                'current_position': self.current_position,
                'position_entry_time': self.position_entry_time.isoformat() if self.position_entry_time else None,
                'position_entry_price': self.position_entry_price,
                'daily_trades': self.daily_trades,
                'daily_profit': self.daily_profit,
                'last_signal': self.last_signal,
                'last_update': datetime.now().isoformat()
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"상태 저장 오류: {e}")

    def initialize_system(self):
        """시스템 초기화"""
        print("\n🔧 시스템 초기화 중...")

        # 1. 상태 로드
        self.load_state()

        # 2. 데이터 수집 및 로드
        print("📊 데이터 로드 중...")
        if not self.data_collector.load_data():
            print("새로운 데이터 수집 중...")
            self.data_collector.collect_all_data()
            self.data_collector.calculate_all_features()
            self.data_collector.save_data()

        # 3. AI 모델 학습
        print("🧠 AI 모델 로드 중...")
        if not self.trading_model.mass_learning():
            print("❌ 모델 학습 실패")
            return False

        # 4. 텔레그램 연결 테스트
        print("📱 텔레그램 연결 테스트...")
        if not self.telegram.test_connection():
            print("❌ 텔레그램 연결 실패")
            return False

        print("✅ 시스템 초기화 완료!")
        return True

    def check_signals(self):
        """신호 체크 및 포지션 변경"""
        try:
            # 최신 데이터 업데이트
            for symbol in ['NVDL', 'NVDQ']:
                realtime_data = self.data_collector.fetch_realtime_data(symbol)
                if realtime_data:
                    self.data_collector.realtime_data[symbol] = realtime_data

            # 포트폴리오 신호 생성
            action, symbol, confidence = self.trading_model.get_portfolio_signal()

            current_time = datetime.now()
            print(f"[{current_time.strftime('%H:%M:%S')}] 신호: {action} {symbol} (신뢰도: {confidence:.2f})")

            # 포지션 변경 조건 확인
            should_change_position = False
            old_position = self.current_position
            new_position = None

            # 매수 신호로 인한 포지션 변경
            if action == "BUY" and confidence >= self.config['min_signal_confidence']:
                if self.current_position != symbol:  # 포지션이 달라질 때만
                    should_change_position = True
                    new_position = symbol

            # 포지션 청산 조건
            elif self.current_position and self.trading_model.should_exit_position():
                should_change_position = True
                new_position = None  # 청산

            # 시간 기반 청산
            elif self.current_position and self.position_entry_time:
                holding_hours = (current_time - self.position_entry_time).total_seconds() / 3600
                if holding_hours > self.config['max_position_time']:
                    should_change_position = True
                    new_position = None  # 청산

            # 포지션이 실제로 변경되는 경우에만 알림 및 처리
            if should_change_position:
                print(f"🔄 포지션 변경 감지: {old_position} → {new_position}")
                self.change_position(old_position, new_position, confidence)
            else:
                # 포지션 변경 없을 때는 콘솔 로그만
                if self.current_position:
                    print(f"📍 포지션 유지: {self.current_position} (변경 없음)")
                else:
                    print(f"💰 현금 유지 (진입 조건 미충족)")

            # 신호 기록 업데이트 (알림과 무관하게)
            new_signal = f"{action}_{symbol}" if action == "BUY" else "HOLD"
            self.last_signal = new_signal
            self.last_signal_time = current_time

            # 신호 히스토리 저장
            self.signal_history.append({
                'timestamp': current_time.isoformat(),
                'action': action,
                'symbol': symbol,
                'confidence': confidence,
                'position': self.current_position,
                'position_changed': should_change_position
            })

            # 히스토리 크기 제한
            if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-500:]

        except Exception as e:
            print(f"신호 체크 오류: {e}")
            self.telegram.notify_error("신호 체크 오류", str(e))

    def change_position(self, old_position: str, new_position: str, confidence: float):
        """포지션 변경 및 알림"""
        print(f"\n🔄 포지션 변경: {old_position} → {new_position}")

        # 기존 포지션 청산 시뮬레이션
        if old_position and self.position_entry_price:
            exit_price = self.get_current_price(old_position)
            if exit_price:
                self.close_position(old_position, exit_price)

        # 새 포지션 진입
        if new_position:
            entry_price = self.get_current_price(new_position)
            if entry_price:
                self.open_position(new_position, entry_price, confidence)

        # 포지션 변경 기록
        self.position_changes.append({
            'timestamp': datetime.now().isoformat(),
            'old_position': old_position,
            'new_position': new_position,
            'confidence': confidence
        })

        # 텔레그램 알림
        analysis = self.generate_position_analysis(new_position, confidence)
        self.telegram.notify_position_change(
            old_position=old_position or "없음",
            new_position=new_position or "없음",
            confidence=confidence,
            analysis=analysis
        )

        # 상태 저장
        self.save_state()

    def open_position(self, symbol: str, entry_price: float, confidence: float):
        """포지션 진입"""
        self.current_position = symbol
        self.position_entry_time = datetime.now()
        self.position_entry_price = entry_price
        self.position_features = self.data_collector.get_latest_features(symbol)

        print(f"📈 {symbol} 포지션 진입: ${entry_price:.2f}")

        if self.auto_trading:
            # 실제 거래 실행 코드 (API 연동 필요)
            print("🤖 자동매매: 실제 주문 실행 (구현 필요)")
        else:
            print("💬 알림 모드: 수동 거래 권장")

    def close_position(self, symbol: str, exit_price: float):
        """포지션 청산"""
        if not self.position_entry_price or not self.position_entry_time:
            return

        # 수익률 계산
        raw_profit = (exit_price / self.position_entry_price - 1) * 100

        # 레버리지 적용
        if symbol == 'NVDL':
            profit_pct = raw_profit * 3  # 3x 레버리지
        elif symbol == 'NVDQ':
            profit_pct = raw_profit * 2  # 2x 역 레버리지
        else:
            profit_pct = raw_profit

        # 보유 시간 계산
        holding_time = self.telegram.format_time_duration(self.position_entry_time)

        # 통계 업데이트
        self.daily_trades += 1
        self.daily_profit += profit_pct
        self.trading_model.total_trades += 1
        self.trading_model.total_profit += profit_pct

        if profit_pct > 0:
            self.trading_model.winning_trades += 1

        self.trading_model.win_rate = (self.trading_model.winning_trades / self.trading_model.total_trades) * 100

        # 성공 거래 학습
        if profit_pct > 0 and self.position_features is not None:
            self.trading_model.record_trade(
                symbol, self.position_entry_price, exit_price, self.position_features
            )

        print(f"📊 {symbol} 포지션 청산: {profit_pct:+.2f}% ({holding_time})")

        # 텔레그램 알림
        self.telegram.notify_trade_result(
            symbol=symbol,
            profit_pct=profit_pct,
            entry_price=self.position_entry_price,
            exit_price=exit_price,
            holding_time=holding_time,
            total_profit=self.trading_model.total_profit,
            win_rate=self.trading_model.win_rate
        )

        # 포지션 초기화
        self.current_position = None
        self.position_entry_time = None
        self.position_entry_price = None
        self.position_features = None

        if self.auto_trading:
            print("🤖 자동매매: 실제 청산 주문 실행 (구현 필요)")

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        if symbol in self.data_collector.realtime_data:
            data = self.data_collector.realtime_data[symbol]
            return data.get('price')
        return None

    def generate_position_analysis(self, symbol: str, confidence: float) -> str:
        """포지션 분석 텍스트 생성"""
        if not symbol:
            return "포지션 청산 권장"

        analysis_parts = []

        if symbol == 'NVDL':
            analysis_parts.append("🟢 NVIDIA 3x 롱 포지션")
            analysis_parts.append("📈 시장 상승 예상")
        elif symbol == 'NVDQ':
            analysis_parts.append("🔴 NASDAQ 2x 숏 포지션")
            analysis_parts.append("📉 시장 하락 예상")

        if confidence > 0.7:
            analysis_parts.append("💪 매우 강한 신호")
        elif confidence > 0.5:
            analysis_parts.append("👍 강한 신호")
        else:
            analysis_parts.append("⚠️ 약한 신호")

        return " | ".join(analysis_parts)

    def send_signal_alert(self, symbol: str, action: str, confidence: float):
        """신호 알림 전송"""
        current_price = self.get_current_price(symbol)
        if not current_price:
            return

        # 기술적 지표 계산
        features = self.data_collector.get_latest_features(symbol)
        rsi = features[9] * 100 if features is not None and len(features) > 9 else 50
        momentum = features[7] if features is not None and len(features) > 7 else 0
        volatility = features[4] if features is not None and len(features) > 4 else 0

        self.telegram.notify_signal_alert(
            symbol=symbol,
            signal=action,
            confidence=confidence,
            current_price=current_price,
            rsi=rsi,
            momentum=momentum,
            volatility=volatility
        )

    def send_daily_summary(self):
        """일일 요약 전송"""
        winning_trades = sum(1 for trade in self.position_changes if trade.get('profit', 0) > 0)

        self.telegram.notify_daily_summary(
            total_trades=self.daily_trades,
            winning_trades=winning_trades,
            daily_profit=self.daily_profit,
            total_profit=self.trading_model.total_profit,
            win_rate=self.trading_model.win_rate,
            current_position=self.current_position or "없음"
        )

    def send_status_update(self):
        """상태 업데이트 전송"""
        uptime = self.telegram.format_time_duration(self.start_time)
        last_signal_time = self.last_signal_time.strftime('%H:%M:%S') if self.last_signal_time else "없음"

        current_pnl = 0.0
        if self.current_position and self.position_entry_price:
            current_price = self.get_current_price(self.current_position)
            if current_price:
                raw_pnl = (current_price / self.position_entry_price - 1) * 100
                if self.current_position == 'NVDL':
                    current_pnl = raw_pnl * 3
                elif self.current_position == 'NVDQ':
                    current_pnl = raw_pnl * 2

        entry_time = self.position_entry_time.strftime('%H:%M:%S') if self.position_entry_time else "없음"

        self.telegram.notify_system_status(
            status="정상 운영",
            uptime=uptime,
            last_signal=f"{self.last_signal} ({last_signal_time})",
            current_position=self.current_position or "없음",
            entry_time=entry_time,
            current_pnl=current_pnl,
            total_trades=self.trading_model.total_trades,
            win_rate=self.trading_model.win_rate,
            total_profit=self.trading_model.total_profit
        )

    def run(self):
        """메인 실행 루프"""
        if not self.initialize_system():
            print("❌ 시스템 초기화 실패")
            return

        print(f"\n🚀 봇 시작 (자동매매: {'켜짐' if self.auto_trading else '꺼짐'})")
        print(f"⏰ 체크 간격: {self.config['check_interval']}초")

        self.running = True
        last_daily_summary = datetime.now().date()
        last_status_update = datetime.now()

        # 시작 알림
        self.telegram.send_message(
            f"🤖 **NVDL/NVDQ 봇 시작**\n\n"
            f"⚡ 모드: {'자동매매' if self.auto_trading else '알림 전용'}\n"
            f"📊 현재 포지션: {self.current_position or '없음'}\n"
            f"⏰ 시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            while self.running:
                # 신호 체크
                self.check_signals()

                # 일일 요약 (지정된 시간에)
                now = datetime.now()
                if (now.date() > last_daily_summary and
                    now.hour >= self.config['daily_summary_hour']):
                    self.send_daily_summary()
                    last_daily_summary = now.date()

                # 상태 업데이트 (정기적)
                if (now - last_status_update).total_seconds() >= self.config['status_update_interval']:
                    self.send_status_update()
                    last_status_update = now

                # 점진적 학습
                self.trading_model.incremental_learning()

                # 상태 저장
                self.save_state()

                # 대기
                time.sleep(self.config['check_interval'])

        except KeyboardInterrupt:
            print("\n⏹️ 사용자에 의한 중단")
        except Exception as e:
            print(f"\n❌ 실행 오류: {e}")
            self.telegram.notify_error("봇 실행 오류", str(e))
        finally:
            self.running = False
            self.telegram.send_message("⏹️ **봇 중단**\n\n시스템이 안전하게 종료되었습니다.")
            print("🔚 봇 종료")

def main():
    """메인 실행 함수"""
    # 설정
    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    AUTO_TRADING = False  # True로 변경 시 자동매매 활성화

    if not FMP_API_KEY or FMP_API_KEY == "YOUR_API_KEY_HERE":
        print("❌ FMP API 키를 설정해주세요!")
        return

    # 봇 생성 및 실행
    bot = NVDLNVDQTelegramBot(FMP_API_KEY, auto_trading=AUTO_TRADING)
    bot.run()

if __name__ == "__main__":
    main()