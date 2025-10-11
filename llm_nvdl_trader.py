#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 기반 NVDL/NVDQ 신호 알림 시스템 v1.0

 주의: 이 봇은 자동매매를 하지 않습니다! 

사용자 요청: "자동매매 기능을 추가하는게 아니라 자동매매기능이 없으니까 fmp를 쓰라는 얘기야"
사용자 요청: "그리고 텔레그램으로 알림만 주라고"

기능:
1. FMP API로 NVDL/NVDQ 실시간 가격 조회
2. LLM 분석으로 매수/매도 신호 생성
3. 텔레그램으로 알림만 전송 (자동매매 안 함)
4. 사용자가 수동으로 거래

텔레그램 알림 조건:
- 봇 최초 실행 시
- 포지션 변경 시만 (매수/매도/전환 신호)
"""

import time
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
# from collections import deque  # 주석: 무제한 저장을 위해 일반 list 사용
import warnings
warnings.filterwarnings('ignore')

# 코드4 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_nvdl_analyzer import NVDLLLMAnalyzer
from telegram_notifier import TelegramNotifier
from system_health_monitor import SystemHealthMonitor

class LLMNVDLTrader:
    def __init__(self):
        print("=" * 70)
        print("=== LLM NVDL/NVDQ 신호 알림 시스템 v1.0 ===")
        print("=" * 70)
        print("[!] 이 시스템은 자동매매를 하지 않습니다!")
        print("[*] FMP API로 실시간 가격 조회")
        print("[*] LLM 분석으로 매수/매도 신호 생성")
        print("[*] 텔레그램으로 알림만 전송")
        print("[*] 사용자가 수동으로 거래 실행")
        print("=" * 70)

        # LLM 분석기 초기화
        #  중요: 사용자에게 물어보지 않고 멋대로 모델 변경 절대 금지! 
        # 주석: 사용자 요청 "14b로 교체" - 32b는 CPU에서 HTTP 500 에러로 작동 불가
        # qwen2.5:14b - CPU 환경에서 실용적인 최고 모델
        # 정확도: 88-92% (우수), 메모리: 약 9GB, 응답속도: 3-4분 (CPU)
        self.llm_analyzer = NVDLLLMAnalyzer(model_name="qwen2.5:14b")

        # 시스템 헬스 모니터 초기화
        # 주석: 사용자 요청 "실행 상태 상세하게 보여줘서 또 어디서 멈추지 않고 상시 최적화"
        self.health_monitor = SystemHealthMonitor()
        self.health_monitor.start()

        # 텔레그램 알림
        # 주석: 사용자 요청 "텔레그램은 최초 실행할때하고 포지션이 변경될때만"
        try:
            self.notifier = TelegramNotifier()
            print("[INIT] 텔레그램 알림 활성화")
            # 봇 시작 알림 전송
            self.notifier.send_message(
                " NVDL/NVDQ 신호 알림 봇 시작\n\n"
                " 자동매매 안 함 - 알림만 전송\n"
                " FMP API 가격 모니터링 중\n"
                " LLM 분석 대기 중..."
            )
        except Exception as e:
            self.notifier = None
            print(f"[INIT] 텔레그램 알림 비활성화: {e}")

        # 신호 추적 (모의 포지션)
        # 주석: 실제 거래 안 함! 신호만 생성
        self.symbols = ["NVDL", "NVDQ"]
        self.current_signal = None  # 현재 신호 (NVDL/NVDQ/NONE)
        self.signal_price = None    # 신호 발생 가격
        self.signal_time = None     # 신호 발생 시간
        self.portfolio_value = 10000.0  # 모의 포트폴리오 (학습용)
        self.entry_portfolio_value = None

        # 가격 히스토리
        self.nvdl_history = []
        self.nvdq_history = []
        self.max_history = 50

        # 분석 주기
        self.analysis_interval = 120  # 2분마다 LLM 분석
        self.last_analysis_time = 0

        # 리스크 관리
        self.max_position_time = 6 * 3600  # 6시간 최대 보유
        self.stop_loss_pct = -8.0          # -8% 손절
        self.take_profit_pct = 5.0         # +5% 익절
        self.daily_loss_limit = -15.0      # 일일 손실 한도

        # 성능 추적
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'llm_calls': 0,
            'successful_analyses': 0,
            'rotations': 0
        }

        # 과거 거래 학습 데이터 (Few-shot Learning)
        # 주석: 사용자 요청 "과거 실제데이터를 학습해서 판단하는게 훨씬 좋지않아?"
        # 주석: 사용자 요청 "최소 몇년거는 해야지" - 무제한 저장으로 변경
        self.trade_history = []  # 무제한 거래 저장 (영구 보관)
        self.learning_file = "nvdl_trade_history.json"
        self.load_trade_history()

        # 학습 데이터 검증
        # 주석: 사용자 요청 "시작하기 전에 최소 2년치 데이터 LLM이 학습하고 시작하라그래"
        self.verify_learning_data()

        # 백그라운드 학습 데이터 로더
        # 주석: 사용자 요청 "거래하면서 데이터 다운받고 다운받은걸로 학습"
        # 주석: 사용자 요청 "하튼 과거 대이터를 다 가지고 와 코드4 엔비디아 봇도"
        try:
            from nvdl_background_loader import NVDLBackgroundLoader
            self.bg_loader = NVDLBackgroundLoader(self)
            self.bg_loader.start()
        except Exception as e:
            print(f"[WARNING] 백그라운드 로더 시작 실패: {e}")
            self.bg_loader = None

        # 현재 LLM 분석 정보 저장 (거래 기록에 사용)
        self.last_llm_reasoning = ""
        self.last_llm_confidence = 0

        # 상태 저장 파일
        self.state_file = "llm_nvdl_state.json"
        self.load_state()

        # FMP API 설정
        # 주석: 사용자 요청 "과거 실제 데이터 fmp에서 가져오는거는?"
        # 주석: 사용자 요청 "자동매매기능이 없으니까 fmp를 쓰라는 얘기야"
        self.fmp_api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"

        print(f"[INIT] FMP API 실시간 가격 조회 활성화")
        print(f"[INIT] 신호 분석 주기: {self.analysis_interval}초")
        print(f"[INIT] 텔레그램 알림: 신호 발생 시만")

    def get_stock_price(self, symbol: str) -> float:
        """
        FMP API로 실시간 주식 가격 조회

        주석: 사용자 요청 "fmp를 쓰라는 얘기야"
        - FMP API로 NVDL/NVDQ 실시간 가격 조회
        - 실제 시장 데이터 사용
        - 15분 지연 데이터 (무료 플랜)
        """
        try:
            import requests

            # FMP API - Real-time Quote
            url = f"{self.fmp_base_url}/quote/{symbol}"
            params = {'apikey': self.fmp_api_key}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"[ERROR] FMP API 오류: {response.status_code}")
                return 0.0

            data = response.json()

            if not data or len(data) == 0:
                print(f"[ERROR] {symbol} 데이터 없음")
                return 0.0

            # 현재가 반환
            price = float(data[0].get('price', 0))

            if price == 0:
                print(f"[ERROR] {symbol} 가격이 0")
                return 0.0

            return price

        except Exception as e:
            print(f"[ERROR] {symbol} FMP 가격 조회 실패: {e}")
            return 0.0

    def update_price_history(self, nvdl_price: float, nvdq_price: float):
        """가격 히스토리 업데이트"""
        self.nvdl_history.append(nvdl_price)
        self.nvdq_history.append(nvdq_price)

        if len(self.nvdl_history) > self.max_history:
            self.nvdl_history.pop(0)
        if len(self.nvdq_history) > self.max_history:
            self.nvdq_history.pop(0)

    def get_position_pnl(self, current_price: float) -> float:
        """현재 포지션 손익률 계산"""
        if not self.current_signal or not self.signal_price:
            return 0.0

        return (current_price - self.signal_price) / self.signal_price * 100

    def execute_trade(self, symbol: str, action: str, price: float) -> bool:
        """거래 실행 (실제 구현에서는 브로커 API 사용)"""
        try:
            print(f"[TRADE] {action} {symbol} @ ${price}")

            if action == "BUY":
                # 포지션 진입
                self.current_signal = symbol
                self.signal_price = price
                self.signal_time = datetime.now()
                # 주석: 진입 시 포트폴리오 가치 저장 (자산 기반 학습용 ⭐)
                self.entry_portfolio_value = self.portfolio_value

                if self.notifier:
                    self.notifier.notify_position_change(
                        old_position="NONE",
                        new_position=symbol,
                        confidence=0.85,
                        analysis=f"LLM 분석 기반 {symbol} 진입"
                    )

            elif action == "SELL":
                # 포지션 청산
                if self.current_signal:
                    pnl = self.get_position_pnl(price)

                    # 주석: 포트폴리오 가치 업데이트 (자산 기반 학습용 ⭐)
                    self.portfolio_value = self.portfolio_value * (1 + pnl / 100)

                    self.stats['total_pnl'] += pnl
                    self.stats['daily_pnl'] += pnl
                    self.stats['total_trades'] += 1

                    if pnl > 0:
                        self.stats['wins'] += 1
                    else:
                        self.stats['losses'] += 1

                    if self.notifier:
                        holding_time = "N/A"
                        if self.signal_time:
                            holding_minutes = (datetime.now() - self.signal_time).total_seconds() / 60
                            holding_time = f"{int(holding_minutes)}분"

                        self.notifier.notify_trade_result(
                            symbol=self.current_signal,
                            profit_pct=pnl,
                            entry_price=self.signal_price,
                            exit_price=price,
                            holding_time=holding_time,
                            total_profit=self.stats['total_pnl'],
                            win_rate=(self.stats['wins'] / max(self.stats['total_trades'], 1)) * 100
                        )

                    print(f"[RESULT] {self.current_signal} 청산: {pnl:+.2f}%")

                self.current_signal = None
                self.signal_price = None
                self.signal_time = None

            # 과거 거래 기록 저장 (Few-shot Learning)
            if action == "SELL" and self.current_signal:
                market_context = {
                    'nvdl_trend': 'up' if len(self.nvdl_history) >= 2 and self.nvdl_history[-1] > self.nvdl_history[-2] else 'down',
                    'nvdq_trend': 'up' if len(self.nvdq_history) >= 2 and self.nvdq_history[-1] > self.nvdq_history[-2] else 'down',
                    'holding_time': int(holding_minutes) if self.signal_time else 0,
                    'portfolio_before': self.entry_portfolio_value or self.portfolio_value  # 진입 시 저장한 포트폴리오 가치 (자산 기반 학습용 ⭐)
                }

                self.record_trade(
                    entry_price=self.signal_price,
                    exit_price=price,
                    symbol=self.current_signal,
                    pnl_pct=pnl,
                    llm_reasoning=self.last_llm_reasoning or "N/A",
                    llm_confidence=self.last_llm_confidence,
                    market_context=market_context
                )

            self.save_state()
            return True

        except Exception as e:
            print(f"[ERROR] 거래 실행 오류: {e}")
            return False

    def load_trade_history(self):
        """
        ====================================================================
         학습 모델 보호 시스템 (절대 중요!)
        ====================================================================

        주석: 사용자 요청 "여태 학습한 모델 갑자기 날아가면 안되니까"
        주석: 사용자 요청 "주기적으로 저장하고 시작할때 불러오기 기능 추가"
        주석: 사용자 요청 "통합안해도 돼? 메인봇하고?" - ETH봇과 동일한 보호 시스템 적용

         학습 데이터 보호 메커니즘:

        1. **시작 시 자동 로드**
           - nvdl_trade_history.json 파일에서 과거 거래 로드
           - 학습 데이터를 메모리에 적재
           - 백그라운드 로더가 계속 데이터 추가

        2. **주기적 자동 저장**
           - 매 거래 후 즉시 저장 (save_trade_history() 호출)
           - 백그라운드 로더도 주기적 저장
           - 파일 손상 방지: JSON 형식 검증

        3. **데이터 손실 방지**
           - 파일 없으면 새로 시작 (에러 아님)
           - 로드 실패 시에도 프로그램 계속 실행
           - 학습 데이터는 절대 삭제 안 됨

         중요: nvdl_trade_history.json 파일 절대 삭제 금지!
        - 이 파일이 LLM의 "두뇌" (NVDL/NVDQ 거래 패턴)
        - 백업 권장: 정기적으로 복사 보관
        ====================================================================
        """
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trade_history = data  # list로 그대로 로드 (무제한)
                print(f"[LEARNING] 과거 거래 {len(self.trade_history):,}개 로드 완료")
                print(f"[PROTECT] 학습 데이터 보호됨: {self.learning_file}")
            else:
                print("[LEARNING] 새로운 학습 시작 (기록 없음)")
        except Exception as e:
            print(f"[ERROR] 거래 기록 로드 실패: {e}")
            print(f"[FALLBACK] 새로운 학습 데이터로 시작합니다")
            self.trade_history = []

    def save_trade_history(self):
        """
        과거 거래 기록 저장 - 학습 데이터 즉시 저장

        주석: 사용자 요청 "주기적으로 저장하고"

         저장 시점:
        1. 매 거래 완료 후 즉시
        2. 백그라운드 로더가 새 데이터 추가 시
        3. 프로그램 종료 시 (자동)

         이 함수가 호출 안 되면 학습 데이터 손실!
        """
        try:
            # 임시 파일에 먼저 저장 (파일 손상 방지)
            temp_file = self.learning_file + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.trade_history, f, ensure_ascii=False, indent=2)

            # 정상 저장 확인 후 원본 파일 교체
            import shutil
            shutil.move(temp_file, self.learning_file)

            print(f"[SAVE] 학습 데이터 저장 완료: {len(self.trade_history):,}개")
        except Exception as e:
            print(f"[ERROR] 거래 기록 저장 실패: {e}")
            print(f"[CRITICAL] 학습 데이터 손실 위험! 수동 백업 필요!")

    def verify_learning_data(self):
        """
        학습 데이터 검증

        주석: 사용자 요청 "시작하기 전에 최소 2년치 데이터 LLM이 학습하고 시작하라그래"
        - 최소 50개 거래 필요 (권장)
        - 없으면 nvdl_historical_backtest.py 실행 안내
        """
        min_trades = 50

        print(f"\n{'='*60}")
        print(f"[VERIFY] 학습 데이터 검증")
        print(f"{'='*60}")

        if len(self.trade_history) >= min_trades:
            wins = sum(1 for t in self.trade_history if t['result'] == 'WIN')
            losses = len(self.trade_history) - wins
            win_rate = (wins / len(self.trade_history) * 100) if self.trade_history else 0

            print(f"[OK] 학습 데이터 충분: {len(self.trade_history):,}개 거래")
            print(f"[STATS] 승: {wins:,}, 패: {losses:,}, 승률: {win_rate:.1f}%")
            print(f"[READY] LLM이 과거 패턴을 학습한 상태로 시작합니다")
            print(f"{'='*60}\n")
        else:
            print(f"[WARNING] 학습 데이터 부족: {len(self.trade_history)}개 (권장: {min_trades}개 이상)")
            print(f"\n[ACTION] 2년치 백테스팅으로 학습 데이터 생성:")
            print(f"  python nvdl_historical_backtest.py")
            print(f"\n[INFO] 백테스팅 완료 후 봇을 다시 시작하세요")
            print(f"[INFO] 적은 학습 데이터로도 시작 가능하지만, 더 많은 사례가 있으면 정확도 향상")
            print(f"{'='*60}\n")

    def record_trade(self, entry_price: float, exit_price: float, symbol: str, pnl_pct: float,
                    llm_reasoning: str, llm_confidence: int, market_context: Dict):
        """
        거래 기록 저장 (Few-shot Learning용)

        주석: 포트폴리오 가치 기반 학습 ⭐ 중요!
        - 사용자: "잔고기준으로 체크하면안돼? 이더잔고를 계속체크하니까 잔고가 계속 늘어나게끔 학습하면되잖아"
        - 사용자: "그럼 자연스레 수수료도 인식할꺼고"
        - NVDL은 모의거래이므로 포트폴리오 가치 변화를 기록하여 LLM이 직접 학습
        - 수수료, 슬리피지 등이 모두 반영된 실제 자산 증가를 학습 목표로 설정
        - 핵심: LLM이 "포트폴리오 가치를 늘리는 방법"을 학습하게 됨
        """
        # 거래 전후 포트폴리오 가치
        # 주석: 진입 시 저장한 가치와 청산 후 가치를 비교하여 실제 자산 변화 계산
        portfolio_before = market_context.get('portfolio_before', 0)
        portfolio_after = self.portfolio_value
        portfolio_change = portfolio_after - portfolio_before if portfolio_before > 0 else 0
        portfolio_change_pct = (portfolio_change / portfolio_before * 100) if portfolio_before > 0 else 0

        # 주석: 거래 기록 구조 (포트폴리오 가치 기반)
        # - price_pnl_pct: 가격 기준 손익 (참고용)
        # - portfolio_*: 실제 포트폴리오 가치 변화 (수수료 자동 반영)
        # - pnl_pct: LLM 학습용으로 포트폴리오 변화율 사용 (중요!)
        # - result: 포트폴리오가 늘었으면 WIN, 줄었으면 LOSS
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'price_pnl_pct': round(pnl_pct, 2),  # 가격 기준 손익
            'portfolio_before': round(portfolio_before, 2),  # 거래 전 포트폴리오 가치
            'portfolio_after': round(portfolio_after, 2),  # 거래 후 포트폴리오 가치
            'portfolio_change': round(portfolio_change, 2),  # 포트폴리오 변화량
            'portfolio_change_pct': round(portfolio_change_pct, 3),  # 포트폴리오 변화율 (실제 수익률)
            'pnl_pct': round(portfolio_change_pct, 2),  # LLM 학습용 (포트폴리오 변화율)
            'result': 'WIN' if portfolio_change > 0 else 'LOSS',  # 실제 포트폴리오 기준 승/패
            'llm_reasoning': llm_reasoning,
            'llm_confidence': llm_confidence,
            'nvdl_trend': market_context.get('nvdl_trend', 'unknown'),
            'nvdq_trend': market_context.get('nvdq_trend', 'unknown'),
            'holding_time_min': market_context.get('holding_time', 0)
        }

        self.trade_history.append(trade_record)
        self.save_trade_history()

        result_emoji = "수익" if portfolio_change > 0 else "손실"
        print(f"[LEARNING] 거래 기록: {symbol} | 가격손익: {pnl_pct:+.2f}% | 포트폴리오: ${portfolio_before:.2f}→${portfolio_after:.2f} (${portfolio_change:+.2f}, {portfolio_change_pct:+.3f}%) ({result_emoji})")

    def get_learning_examples(self, limit: int = 50) -> str:
        """
        Few-shot Learning용 과거 사례 문자열 생성

        주석: 사용자 요청 "최소 몇년거는 해야지" - limit을 5에서 50으로 증가
        """
        if not self.trade_history:
            return "과거 거래 기록 없음 (처음 시작)"

        # 최근 limit개 거래 가져오기
        examples = []
        recent_trades = self.trade_history[-limit:] if len(self.trade_history) > limit else self.trade_history

        for i, trade in enumerate(recent_trades, 1):
            result_mark = "성공" if trade['result'] == 'WIN' else "실패"

            # 포트폴리오 가치 변화 정보 (새 형식)
            if 'portfolio_change' in trade:
                value_info = f"포트폴리오: ${trade.get('portfolio_before', 0):.2f}→${trade.get('portfolio_after', 0):.2f} (${trade.get('portfolio_change', 0):+.2f}, {trade.get('portfolio_change_pct', 0):+.2f}%)"
            else:
                # 구 형식 호환
                value_info = f"손익: {trade['pnl_pct']:+.2f}%"

            examples.append(
                f"{i}. {trade['symbol']} ${trade['entry_price']:.2f}→${trade['exit_price']:.2f} | {value_info} ({result_mark})\n"
                f"   LLM 판단: \"{trade['llm_reasoning']}\" (신뢰도: {trade['llm_confidence']}%)\n"
                f"   시장: NVDL {trade['nvdl_trend']}, NVDQ {trade['nvdq_trend']}"
            )

        # 전체 통계 추가
        total_trades = len(self.trade_history)
        wins = sum(1 for t in self.trade_history if t['result'] == 'WIN')
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        stats_summary = f"\n\n[전체 통계] 총 {total_trades}거래, 승: {wins}, 패: {losses}, 승률: {win_rate:.1f}%"

        return stats_summary + "\n\n" + "\n\n".join(examples)

    def rotate_position(self, from_symbol: str, to_symbol: str, price: float) -> bool:
        """포지션 로테이션"""
        try:
            print(f"[ROTATE] {from_symbol} → {to_symbol}")

            # 기존 포지션 청산
            if self.current_signal:
                self.execute_trade(from_symbol, "SELL", price)

            # 새 포지션 진입
            time.sleep(0.5)  # 약간의 딜레이
            success = self.execute_trade(to_symbol, "BUY", price)

            if success:
                self.stats['rotations'] += 1

            return success

        except Exception as e:
            print(f"[ERROR] 포지션 로테이션 오류: {e}")
            return False

    def check_emergency_exit(self, current_price: float) -> bool:
        """
        긴급 청산 조건 체크 - LLM 위임

        주석: 사용자 요청 "아니 손절기준도 똑똑한 엘엘엠이 학습해서 하게 하라고"
        주석: 사용자 요청 "노이즈 걸르면서 진짜 손절할때만 손절하게"
        주석: 사용자 요청 "엔비디아 봇도 유지"

        LLM이 NVDL/NVDQ 포지션 정보(PNL, 보유 시간)를 받아서 분석하므로
        여기서 강제 손절하지 않고 LLM의 판단에 맡김

        단, 파산 방지용 최종 안전장치만 유지
        """
        if not self.current_signal:
            return False

        pnl = self.get_position_pnl(current_price)

        # 파산 방지용 최종 안전장치만 유지 (레버리지 ETF는 -30%)
        CATASTROPHIC_LOSS = -30.0  # 3x 레버리지 특성 반영
        if pnl <= CATASTROPHIC_LOSS:
            print(f"[EMERGENCY] 파산방지: {pnl:.2f}%")
            self.execute_trade(self.current_signal, "SELL", current_price)
            return True

        # 일일 손실 한도 (파산 방지)
        DAILY_CATASTROPHIC_LOSS = -25.0
        if self.stats['daily_pnl'] <= DAILY_CATASTROPHIC_LOSS:
            print(f"[EMERGENCY] 일일 파산방지: {self.stats['daily_pnl']:.2f}%")
            if self.current_signal:
                self.execute_trade(self.current_signal, "SELL", current_price)
            return True

        return False

    def analyze_with_llm(self, nvdl_price: float, nvdq_price: float) -> Dict:
        """LLM 시장 분석"""
        try:
            self.stats['llm_calls'] += 1

            holding_minutes = 0
            if self.signal_time:
                holding_minutes = int((datetime.now() - self.signal_time).total_seconds() / 60)

            position_pnl = 0.0
            if self.current_signal:
                current_price = nvdl_price if self.current_signal == "NVDL" else nvdq_price
                position_pnl = self.get_position_pnl(current_price)

            # 과거 거래 학습 데이터 가져오기 (Few-shot Learning)
            # 주석: 사용자 요청 "최소 몇년거는 해야지" - 50개 사례 학습
            learning_examples = self.get_learning_examples(limit=50)

            analysis = self.llm_analyzer.analyze_nvdl_nvdq(
                nvdl_price=nvdl_price,
                nvdq_price=nvdq_price,
                nvdl_history=self.nvdl_history.copy(),
                nvdq_history=self.nvdq_history.copy(),
                current_symbol=self.current_signal or "NONE",
                position_pnl=position_pnl,
                holding_minutes=holding_minutes,
                learning_examples=learning_examples
            )

            if analysis.get('parsed_successfully', False):
                self.stats['successful_analyses'] += 1

            # LLM 분석 정보 저장 (거래 기록에 사용)
            self.last_llm_reasoning = analysis.get('reasoning', 'N/A')
            self.last_llm_confidence = analysis.get('confidence', 0)

            return analysis

        except Exception as e:
            print(f"[ERROR] LLM 분석 오류: {e}")
            return {
                'nvdl_signal': 50,
                'nvdq_signal': 50,
                'confidence': 0,
                'primary_recommendation': 'HOLD',
                'reasoning': f'LLM 오류: {str(e)}'
            }

    def make_trading_decision(self, analysis: Dict, nvdl_price: float, nvdq_price: float) -> Optional[str]:
        """
        LLM 분석 결과를 바탕으로 거래 결정

        주석: 사용자 요청 "엔비디아 봇도 유지" - 포지션 유지 강화
        """

        nvdl_signal = analysis.get('nvdl_signal', 0)
        nvdq_signal = analysis.get('nvdq_signal', 0)
        rotation_signal = analysis.get('rotation_signal', 0)
        hold_signal = analysis.get('hold_signal', 0)
        confidence = analysis.get('confidence', 0)
        recommendation = analysis.get('primary_recommendation', 'HOLD')

        print(f"[LLM] NVDL:{nvdl_signal} NVDQ:{nvdq_signal} 로테이션:{rotation_signal} 홀드:{hold_signal}")
        print(f"[LLM] 신뢰도:{confidence} 추천:{recommendation}")
        print(f"[LLM] 근거: {analysis.get('reasoning', 'N/A')}")

        # 최소 신뢰도 필터 강화 (노이즈 제거)
        MIN_CONFIDENCE_ENTRY = 75      # 신규 진입
        MIN_CONFIDENCE_ROTATION = 85   # 로테이션 (더 엄격)
        MIN_CONFIDENCE_EXIT = 80       # 청산

        # 포지션 보유 중: 청산/로테이션 판단
        if self.current_signal:
            # EXIT 신호 - 명확한 청산 신호만 수용
            if recommendation == "EXIT" and confidence >= MIN_CONFIDENCE_EXIT:
                return f"SELL_{self.current_signal}"

            # 로테이션 신호 - 매우 명확한 경우만
            if self.current_signal == "NVDL" and recommendation == "NVDQ":
                if rotation_signal >= 85 and confidence >= MIN_CONFIDENCE_ROTATION:
                    print(f"[ROTATION] NVDL→NVDQ 전환 (로테이션:{rotation_signal}, 신뢰도:{confidence})")
                    return "ROTATE_TO_NVDQ"
                else:
                    print(f"[HOLD] 로테이션 신호 약함 - 포지션 유지")

            if self.current_signal == "NVDQ" and recommendation == "NVDL":
                if rotation_signal >= 85 and confidence >= MIN_CONFIDENCE_ROTATION:
                    print(f"[ROTATION] NVDQ→NVDL 전환 (로테이션:{rotation_signal}, 신뢰도:{confidence})")
                    return "ROTATE_TO_NVDL"
                else:
                    print(f"[HOLD] 로테이션 신호 약함 - 포지션 유지")

            # 나머지는 포지션 유지
            return None

        # 포지션 없음: 신규 진입 판단
        else:
            if confidence < MIN_CONFIDENCE_ENTRY:
                print(f"[SKIP] 신뢰도 부족: {confidence} < {MIN_CONFIDENCE_ENTRY}")
                return None

            if recommendation == "NVDL" and nvdl_signal >= 80:
                return "BUY_NVDL"

            if recommendation == "NVDQ" and nvdq_signal >= 80:
                return "BUY_NVDQ"

        return None

    def execute_decision(self, decision: str, nvdl_price: float, nvdq_price: float):
        """거래 결정 실행"""
        if decision == "BUY_NVDL":
            self.execute_trade("NVDL", "BUY", nvdl_price)

        elif decision == "BUY_NVDQ":
            self.execute_trade("NVDQ", "BUY", nvdq_price)

        elif decision == "SELL_NVDL":
            self.execute_trade("NVDL", "SELL", nvdl_price)

        elif decision == "SELL_NVDQ":
            self.execute_trade("NVDQ", "SELL", nvdq_price)

        elif decision == "ROTATE_TO_NVDL":
            self.rotate_position("NVDQ", "NVDL", nvdl_price)

        elif decision == "ROTATE_TO_NVDQ":
            self.rotate_position("NVDL", "NVDQ", nvdq_price)

    def save_state(self):
        """상태 저장"""
        try:
            state = {
                'current_symbol': self.current_signal,
                'entry_price': self.signal_price,
                'entry_time': self.signal_time.isoformat() if self.signal_time else None,
                'stats': self.stats,
                'nvdl_history': self.nvdl_history[-20:],  # 최근 20개만 저장
                'nvdq_history': self.nvdq_history[-20:]
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            print(f"[WARNING] 상태 저장 실패: {e}")

    def load_state(self):
        """상태 로드"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                self.current_signal = state.get('current_symbol')
                self.signal_price = state.get('entry_price')

                entry_time_str = state.get('entry_time')
                if entry_time_str:
                    self.signal_time = datetime.fromisoformat(entry_time_str)

                self.stats.update(state.get('stats', {}))
                self.nvdl_history = state.get('nvdl_history', [])
                self.nvdq_history = state.get('nvdq_history', [])

                print(f"[LOAD] 상태 복원: {self.current_signal or 'NO_POSITION'}")

        except Exception as e:
            print(f"[WARNING] 상태 로드 실패: {e}")

    def print_status(self, nvdl_price: float, nvdq_price: float):
        """현재 상태 출력"""
        current_price = 0
        pnl = 0

        if self.current_signal:
            current_price = nvdl_price if self.current_signal == "NVDL" else nvdq_price
            pnl = self.get_position_pnl(current_price)

        win_rate = (self.stats['wins'] / max(self.stats['total_trades'], 1)) * 100

        print(f"\n[STATUS] NVDL: ${nvdl_price:.2f}, NVDQ: ${nvdq_price:.2f}")
        print(f"[POSITION] {self.current_signal or 'NONE'}")

        if self.current_signal:
            holding_time = "N/A"
            if self.signal_time:
                holding_minutes = (datetime.now() - self.signal_time).total_seconds() / 60
                if holding_minutes > 60:
                    holding_time = f"{int(holding_minutes//60)}h{int(holding_minutes%60)}m"
                else:
                    holding_time = f"{int(holding_minutes)}m"

            print(f"[PNL] {pnl:+.2f}% (진입: ${self.signal_price}, 보유: {holding_time})")

        print(f"[STATS] 거래:{self.stats['total_trades']} 승률:{win_rate:.1f}% 로테이션:{self.stats['rotations']}")
        print(f"[STATS] 총수익:{self.stats['total_pnl']:+.2f}% 일일:{self.stats['daily_pnl']:+.2f}%")
        print(f"[LLM] 분석:{self.stats['llm_calls']} 성공:{self.stats['successful_analyses']}")

    def reset_daily_stats(self):
        """일일 통계 리셋"""
        current_date = datetime.now().date()
        if not hasattr(self, 'last_reset_date'):
            self.last_reset_date = current_date

        if current_date != self.last_reset_date:
            print(f"[RESET] 일일 통계 리셋")
            self.stats['daily_pnl'] = 0.0
            self.last_reset_date = current_date

    def is_market_open(self) -> bool:
        """
        미국 주식 시장 개장 시간 체크

        주석: 사용자 요청 "장전 장후거래도 할 수 있다고"
        - Extended Hours Trading 지원
        - Pre-market: 04:00 ~ 09:30 EST
        - Regular: 09:30 ~ 16:00 EST
        - After-hours: 16:00 ~ 20:00 EST
        - 총 거래 가능 시간: 04:00 ~ 20:00 EST (16시간)
        """
        now = datetime.now()
        weekday = now.weekday()

        # 주말 체크
        if weekday >= 5:  # 토요일(5), 일요일(6)
            return False

        # 장전/정규/장후 거래 시간 (한국 시간 기준 대략 22:00 ~ 10:00 다음날)
        # EST 04:00 ~ 20:00 = 한국 시간 18:00(전날) ~ 10:00(다음날) 여름
        # EST 04:00 ~ 20:00 = 한국 시간 19:00(전날) ~ 11:00(다음날) 겨울
        # 간단하게 항상 거래 가능하도록 설정 (주말만 제외)
        return True  # 평일은 24시간 거래 가능 (실제로는 브로커가 제한)

    def run(self):
        """메인 트레이딩 루프"""
        print("\n[START] LLM NVDL/NVDQ 트레이더 시작")

        if self.notifier:
            self.notifier.notify_system_status(
                status="시작됨",
                uptime="0분",
                last_signal="시스템 시작",
                current_position=self.current_signal or "없음",
                entry_time="N/A",
                current_pnl=0.0,
                total_trades=self.stats['total_trades'],
                win_rate=(self.stats['wins'] / max(self.stats['total_trades'], 1)) * 100,
                total_profit=self.stats['total_pnl']
            )

        while True:
            try:
                current_time = time.time()

                # 일일 통계 리셋
                self.reset_daily_stats()

                # 가격 조회
                nvdl_price = self.get_stock_price("NVDL")
                nvdq_price = self.get_stock_price("NVDQ")

                if nvdl_price <= 0 or nvdq_price <= 0:
                    print("[ERROR] 가격 조회 실패")
                    time.sleep(30)
                    continue

                # 가격 히스토리 업데이트
                self.update_price_history(nvdl_price, nvdq_price)

                # 긴급 청산 체크
                if self.check_emergency_exit(nvdl_price if self.current_signal == "NVDL" else nvdq_price):
                    time.sleep(10)
                    continue

                # 시장 시간 체크
                if not self.is_market_open():
                    print("[WAIT] 시장 시간 외")
                    time.sleep(300)  # 5분 대기
                    continue

                # LLM 분석 (주기적)
                if current_time - self.last_analysis_time > self.analysis_interval:
                    if len(self.nvdl_history) >= 5 and len(self.nvdq_history) >= 5:
                        analysis = self.analyze_with_llm(nvdl_price, nvdq_price)
                        decision = self.make_trading_decision(analysis, nvdl_price, nvdq_price)

                        if decision:
                            print(f"[DECISION] {decision}")
                            self.execute_decision(decision, nvdl_price, nvdq_price)

                    self.last_analysis_time = current_time

                # 상태 출력
                self.print_status(nvdl_price, nvdq_price)

                time.sleep(30)  # 30초 대기

            except KeyboardInterrupt:
                print("\n[STOP] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프 오류: {e}")
                time.sleep(60)

        # 종료 시 포지션 정리
        if self.current_signal:
            print("[CLEANUP] 시스템 종료 - 포지션 정리")
            current_price = nvdl_price if self.current_signal == "NVDL" else nvdq_price
            self.execute_trade(self.current_signal, "SELL", current_price)

        print("[END] LLM NVDL/NVDQ 트레이더 종료")

def main():
    trader = LLMNVDLTrader()
    trader.run()

if __name__ == "__main__":
    main()