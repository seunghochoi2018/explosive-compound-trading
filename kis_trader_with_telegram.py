#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 텔레그램 알림 자동매매 시스템
- 기존 KIS TRADER 매매 로직 그대로 유지
- 시작 시 최초 포지션 텔레그램 알림
- 포지션 변경 시마다 텔레그램 알림
"""

import os
import yaml
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class TelegramNotifier:
    """텔레그램 알림 시스템"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        텔레그램 알림 시스템 초기화

        Args:
            bot_token: 텔레그램 봇 토큰
            chat_id: 대화방 ID
        """
        # 설정 파일에서 읽거나 기본값 사용
        config_file = "telegram_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.bot_token = config.get('bot_token', bot_token)
                self.chat_id = config.get('chat_id', chat_id)
        else:
            # 기본값 (코드3에서 사용된 것)
            self.bot_token = bot_token or "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
            self.chat_id = chat_id or "7805944420"

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

        print(f"[텔레그램] 알림 시스템 초기화 완료")
        print(f"  채팅 ID: {self.chat_id}")

    def send_message(self, message: str, disable_notification: bool = False) -> bool:
        """
        텔레그램 메시지 전송

        Args:
            message: 전송할 메시지
            disable_notification: 무음 알림 여부

        Returns:
            전송 성공 여부
        """
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_notification': disable_notification
            }

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            return True

        except Exception as e:
            print(f"[텔레그램 오류] 메시지 전송 실패: {e}")
            return False

    def notify_initial_position(self, positions: List[Dict], usd_cash: float):
        """
        시작 시 최초 포지션 알림

        Args:
            positions: 현재 포지션 리스트
            usd_cash: USD 현금 잔고
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if positions:
            pos = positions[0]
            message = f"""
 **KIS 자동매매 시작**

⏰ **시작 시간**: {timestamp}

 **현재 포지션**:
   종목: {pos['symbol']}
   수량: {pos['qty']:.0f}주
   평균가: ${pos['avg_price']:.2f}
   현재가: ${pos['current_price']:.2f}
   손익: {pos['pnl_pct']:+.2f}%

 **USD 현금**: ${usd_cash:.2f}

 **시스템**: 정상 가동 중
            """.strip()
        else:
            message = f"""
 **KIS 자동매매 시작**

⏰ **시작 시간**: {timestamp}

 **현재 포지션**: 없음

 **USD 현금**: ${usd_cash:.2f}

 **시스템**: 정상 가동 중
            """.strip()

        self.send_message(message)

    def notify_position_change(self, action: str, symbol: str, quantity: int,
                              reason: str, old_position: str = None,
                              old_pnl_pct: float = None):
        """
        포지션 변경 알림

        Args:
            action: 'BUY' 또는 'SELL'
            symbol: 종목 코드
            quantity: 수량
            reason: 변경 사유
            old_position: 이전 포지션 (청산 시)
            old_pnl_pct: 이전 포지션 손익률 (청산 시)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if action == 'BUY':
            emoji = ""
            action_text = "매수 진입"
            message = f"""
{emoji} **{action_text}**

⏰ **시간**: {timestamp}

 **종목**: {symbol}
 **수량**: {quantity}주

 **사유**: {reason}

 **전략**: KIS 추세돌파
            """.strip()

        elif action == 'SELL':
            emoji = ""
            action_text = "매도 청산"
            result_emoji = "" if old_pnl_pct and old_pnl_pct > 0 else ""

            message = f"""
{emoji} **{action_text}**

⏰ **시간**: {timestamp}

 **종목**: {symbol}
 **수량**: {quantity}주

 **손익**: {result_emoji} {old_pnl_pct:+.2f}%

 **사유**: {reason}

 **전략**: KIS 추세돌파
            """.strip()

        self.send_message(message)

    def notify_trade_summary(self, total_trades: int, wins: int, losses: int,
                           total_pnl: float, current_position: str = None):
        """
        거래 요약 알림

        Args:
            total_trades: 총 거래 횟수
            wins: 수익 거래 횟수
            losses: 손실 거래 횟수
            total_pnl: 누적 손익률
            current_position: 현재 포지션
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        message = f"""
 **거래 요약**

⏰ **시간**: {timestamp}

 **거래 현황**:
  - 총 거래: {total_trades}회
  - 수익: {wins}회
  - 손실: {losses}회
  - 승률: {win_rate:.1f}%

 **누적 손익**: {total_pnl:+.2f}%

 **현재 포지션**: {current_position or '없음'}

 **시스템**: 정상 운영 중
        """.strip()

        self.send_message(message, disable_notification=True)

    def notify_error(self, error_type: str, error_message: str):
        """
        오류 알림

        Args:
            error_type: 오류 유형
            error_message: 오류 메시지
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = f"""
 **시스템 오류 알림**

⏰ **시간**: {timestamp}

 **오류 유형**: {error_type}

 **내용**: {error_message}

 **조치 필요**
        """.strip()

        self.send_message(message)

    def test_connection(self) -> bool:
        """텔레그램 연결 테스트"""
        try:
            test_message = f" **연결 테스트**\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n KIS 트레이더 텔레그램 봇 정상 작동"
            return self.send_message(test_message)
        except Exception as e:
            print(f"[텔레그램] 연결 테스트 실패: {e}")
            return False


class KISAutoTraderWithTelegram:
    """한국투자증권 텔레그램 알림 자동매매 시스템"""

    def __init__(self, config_path: str = "kis_devlp.yaml", initial_usd: float = None,
                 enable_telegram: bool = True):
        """
        초기화

        Args:
            config_path: 설정 파일 경로
            initial_usd: 초기 USD 입금액 (None이면 실제 잔고로 자동 설정)
            enable_telegram: 텔레그램 알림 사용 여부
        """
        print("="*80)
        print("한국투자증권 텔레그램 알림 자동매매 시스템 v2.0")
        print("="*80)

        # 텔레그램 알림 시스템 초기화
        self.enable_telegram = enable_telegram
        if self.enable_telegram:
            try:
                self.telegram = TelegramNotifier()
                if not self.telegram.test_connection():
                    print("[경고] 텔레그램 연결 실패, 알림 없이 계속 진행")
                    self.enable_telegram = False
            except Exception as e:
                print(f"[경고] 텔레그램 초기화 실패: {e}")
                self.enable_telegram = False

        # 설정 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 토큰 로드
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            self.access_token = token_data['access_token']

        # 계좌번호
        acct_parts = self.config['my_acct'].split('-')
        self.cano = acct_parts[0]
        self.acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

        # API URL
        self.base_url = "https://openapi.koreainvestment.com:9443"

        # 거래 설정
        self.exchange_cd = "NASD"
        self.exchange_cd_buy = "AMEX"
        self.currency = "USD"

        # 거래 대상 종목
        self.target_symbols = ['SOXL', 'SOXS']

        # 추세돌파 전략 파라미터
        self.trend_signal = None
        self.last_signal_change = None
        self.position_entry_time = None
        self.max_profit_pct = 0.0

        # 전략 설정
        self.max_position_time = 30 * 60
        self.take_profit_target = 1.0
        self.stop_loss_pct = -0.5
        self.min_profit_to_hold = 0.3
        self.profit_decay_threshold = 0.1

        # 가격 히스토리
        self.price_history = []
        self.max_history_len = 20

        # 거래 기록
        self.trade_history = []
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0
        }

        # 초기 USD 설정
        if initial_usd is None:
            buying_power = self.get_usd_cash_balance("SOXL", 40.0)
            if buying_power['success']:
                self.initial_usd = buying_power['ord_psbl_frcr_amt']
            else:
                self.initial_usd = 0.0
        else:
            self.initial_usd = initial_usd

        print(f"[초기화 완료]")
        print(f"  계좌: {self.cano}-{self.acnt_prdt_cd}")
        print(f"  초기 USD: ${self.initial_usd:.2f}")
        print(f"  거래 종목: {', '.join(self.target_symbols)}")
        print(f"  텔레그램 알림: {'활성화' if self.enable_telegram else '비활성화'}")
        print("="*80)

        # 시작 시 최초 포지션 알림
        if self.enable_telegram:
            positions = self.get_positions()
            self.telegram.notify_initial_position(positions, self.initial_usd)

    def get_usd_cash_balance(self, symbol: str = "SOXL", price: float = 40.0) -> Dict:
        """USD 현금 잔고 조회"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3007R",
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "AMEX",
            "OVRS_ORD_UNPR": str(price),
            "ITEM_CD": symbol
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            result = response.json()

            if result.get('rt_cd') != '0':
                return {'success': False, 'error': result.get('msg1', '')}

            output = result.get('output', {})

            ord_psbl_cash = float(output.get('ord_psbl_cash', '0').replace(',', ''))
            ord_psbl_frcr_amt = float(output.get('ord_psbl_frcr_amt', '0').replace(',', ''))
            max_ord_psbl_qty = int(float(output.get('max_ord_psbl_qty', '0')))

            return {
                'success': True,
                'ord_psbl_cash': ord_psbl_cash,
                'ord_psbl_frcr_amt': ord_psbl_frcr_amt,
                'max_ord_psbl_qty': max_ord_psbl_qty
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_positions(self) -> List[Dict]:
        """보유 포지션 조회"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3012R",
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "TR_CRCY_CD": self.currency,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                return []

            result = response.json()

            if result.get('rt_cd') != '0':
                return []

            output1 = result.get('output1', [])
            positions = []

            for item in output1:
                symbol = item.get('ovrs_pdno', '')
                qty = float(item.get('ovrs_cblc_qty', '0'))

                if qty > 0 and symbol in self.target_symbols:
                    avg_price = float(item.get('pchs_avg_pric', '0'))
                    current_price = float(item.get('now_pric2', '0'))
                    eval_amt = float(item.get('ovrs_stck_evlu_amt', '0'))

                    pnl = eval_amt - (qty * avg_price)
                    pnl_pct = (pnl / (qty * avg_price) * 100) if avg_price > 0 else 0

                    positions.append({
                        'symbol': symbol,
                        'qty': qty,
                        'avg_price': avg_price,
                        'current_price': current_price,
                        'eval_amt': eval_amt,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })

            return positions

        except Exception as e:
            print(f"[ERROR] 포지션 조회 오류: {e}")
            if self.enable_telegram:
                self.telegram.notify_error("포지션 조회 오류", str(e))
            return []

    def get_hashkey(self, data: dict) -> str:
        """해시키 생성"""
        url = f"{self.base_url}/uapi/hashkey"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get('HASH', '')
        except Exception as e:
            print(f"[ERROR] 해시키 생성 실패: {e}")

        return ""

    def buy_stock(self, symbol: str, quantity: int) -> Dict:
        """해외주식 매수"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        order_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }

        hashkey = self.get_hashkey(order_data)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT1002U",
            "custtype": "P",
            "hashkey": hashkey,
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        try:
            response = requests.post(url, headers=headers, json=order_data, timeout=10)

            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            result = response.json()

            if result.get('rt_cd') == '0':
                return {
                    'success': True,
                    'order_no': result.get('output', {}).get('odno', ''),
                    'message': result.get('msg1', ''),
                    'symbol': symbol,
                    'quantity': quantity
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg1', ''),
                    'msg_cd': result.get('msg_cd', '')
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def sell_stock(self, symbol: str, quantity: int) -> Dict:
        """해외주식 매도"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        order_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }

        hashkey = self.get_hashkey(order_data)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT1006U",
            "custtype": "P",
            "hashkey": hashkey,
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        try:
            response = requests.post(url, headers=headers, json=order_data, timeout=10)

            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            result = response.json()

            if result.get('rt_cd') == '0':
                return {
                    'success': True,
                    'order_no': result.get('output', {}).get('odno', ''),
                    'message': result.get('msg1', ''),
                    'symbol': symbol,
                    'quantity': quantity
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg1', ''),
                    'msg_cd': result.get('msg_cd', '')
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def detect_trend_signal(self) -> Optional[str]:
        """추세 신호 감지"""
        if len(self.price_history) < 10:
            return None

        recent = self.price_history[-10:]
        ma_short = sum(recent[-5:]) / 5
        ma_long = sum(recent) / 10
        current = recent[-1]

        if ma_short > ma_long and current > ma_short:
            return 'BULL'
        elif ma_short < ma_long and current < ma_short:
            return 'BEAR'

        return None

    def should_exit_for_profit_decay(self, current_pnl_pct: float) -> bool:
        """수익 0 수렴 청산 체크"""
        if current_pnl_pct > self.max_profit_pct:
            self.max_profit_pct = current_pnl_pct

        if self.max_profit_pct >= self.min_profit_to_hold:
            if current_pnl_pct <= self.profit_decay_threshold:
                return True

        return False

    def execute_strategy(self):
        """추세돌파 전략 실행 (메인 로직)"""
        print("\n" + "="*80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 전략 실행")
        print("="*80)

        # 1. USD 현금 잔고 조회
        buying_power = self.get_usd_cash_balance("SOXL", 40.0)

        if not buying_power['success']:
            print(f"[ERROR] USD 현금 조회 실패: {buying_power.get('error')}")
            if self.enable_telegram:
                self.telegram.notify_error("USD 잔고 조회 실패", buying_power.get('error'))
            return

        usd_cash = buying_power['ord_psbl_frcr_amt']

        # 2. 보유 포지션 조회
        positions = self.get_positions()

        print(f"\n[계좌 현황]")
        print(f"  USD 현금: ${usd_cash:.2f}")

        current_position = None
        current_qty = 0
        current_avg_price = 0
        current_pnl_pct = 0

        if positions:
            pos = positions[0]
            current_position = pos['symbol']
            current_qty = pos['qty']
            current_avg_price = pos['avg_price']
            current_pnl_pct = pos['pnl_pct']
            current_price = pos['current_price']

            print(f"  보유: {current_position} {current_qty}주 @ ${current_avg_price:.2f}")
            print(f"  손익: {current_pnl_pct:+.2f}%")

            self.price_history.append(current_price)
            if len(self.price_history) > self.max_history_len:
                self.price_history.pop(0)
        else:
            print(f"  보유: 없음")

        # 3. 추세 신호 감지
        new_signal = self.detect_trend_signal()

        if new_signal:
            print(f"\n[추세 신호] {new_signal}")
            if new_signal != self.trend_signal:
                print(f"  신호 변경: {self.trend_signal} -> {new_signal}")
                self.last_signal_change = datetime.now()
            self.trend_signal = new_signal

        # 4. 청산 조건 체크
        should_exit = False
        exit_reason = ""

        if current_position:
            signal_to_symbol = {'BULL': 'SOXL', 'BEAR': 'SOXS'}
            target_symbol = signal_to_symbol.get(self.trend_signal)

            if target_symbol and target_symbol != current_position:
                should_exit = True
                exit_reason = f"신호 변경 ({self.trend_signal})"

            elif self.should_exit_for_profit_decay(current_pnl_pct):
                should_exit = True
                exit_reason = f"수익 0 수렴 (최고 {self.max_profit_pct:.2f}% -> 현재 {current_pnl_pct:.2f}%)"

            elif current_pnl_pct >= self.take_profit_target:
                should_exit = True
                exit_reason = f"목표 수익 달성 ({current_pnl_pct:.2f}%)"

            elif current_pnl_pct <= self.stop_loss_pct:
                should_exit = True
                exit_reason = f"손절 ({current_pnl_pct:.2f}%)"

            if self.position_entry_time:
                holding_time = (datetime.now() - self.position_entry_time).total_seconds()
                if holding_time > self.max_position_time:
                    should_exit = True
                    exit_reason = f"최대 보유 시간 초과 ({holding_time/60:.0f}분)"

        # 5. 청산 실행
        if should_exit:
            print(f"\n[청산 실행] {exit_reason}")
            print(f"  매도: {current_position} {int(current_qty)}주")

            result = self.sell_stock(current_position, int(current_qty))

            if result['success']:
                print(f"  [SUCCESS] 주문번호: {result['order_no']}")
                print(f"  메시지: {result['message']}")

                # 텔레그램 알림
                if self.enable_telegram:
                    self.telegram.notify_position_change(
                        action='SELL',
                        symbol=current_position,
                        quantity=int(current_qty),
                        reason=exit_reason,
                        old_position=current_position,
                        old_pnl_pct=current_pnl_pct
                    )

                # 통계 업데이트
                self.stats['total_trades'] += 1
                if current_pnl_pct > 0:
                    self.stats['wins'] += 1
                else:
                    self.stats['losses'] += 1
                self.stats['total_pnl'] += current_pnl_pct

                # 기록 저장
                self.trade_history.append({
                    'type': 'SELL',
                    'symbol': current_position,
                    'quantity': int(current_qty),
                    'pnl_pct': current_pnl_pct,
                    'reason': exit_reason,
                    'timestamp': datetime.now().isoformat()
                })

                # 리셋
                self.max_profit_pct = 0.0
                self.position_entry_time = None
                current_position = None

                # 청산 후 잔고 재조회
                time.sleep(2)
                buying_power = self.get_usd_cash_balance("SOXL", 40.0)
                if buying_power['success']:
                    usd_cash = buying_power['ord_psbl_frcr_amt']

            else:
                print(f"  [FAIL] {result.get('error')}")
                if self.enable_telegram:
                    self.telegram.notify_error("매도 실패", result.get('error'))

        # 6. 신규 진입
        if not current_position and self.trend_signal:
            signal_to_symbol = {'BULL': 'SOXL', 'BEAR': 'SOXS'}
            target_symbol = signal_to_symbol[self.trend_signal]

            if usd_cash > 0:
                max_qty = int(usd_cash / 40.0)
                buy_qty = min(max(1, max_qty), 10)

                print(f"\n[신규 진입] {target_symbol} {buy_qty}주 매수")

                result = self.buy_stock(target_symbol, buy_qty)

                if result['success']:
                    print(f"  [SUCCESS] 주문번호: {result['order_no']}")
                    print(f"  메시지: {result['message']}")

                    # 텔레그램 알림
                    if self.enable_telegram:
                        self.telegram.notify_position_change(
                            action='BUY',
                            symbol=target_symbol,
                            quantity=buy_qty,
                            reason=f"추세 진입 ({self.trend_signal})"
                        )

                    self.position_entry_time = datetime.now()
                    self.max_profit_pct = 0.0

                    # 기록 저장
                    self.trade_history.append({
                        'type': 'BUY',
                        'symbol': target_symbol,
                        'quantity': buy_qty,
                        'reason': f"추세 진입 ({self.trend_signal})",
                        'timestamp': datetime.now().isoformat()
                    })

                else:
                    print(f"  [FAIL] {result.get('error')}")
                    if self.enable_telegram:
                        self.telegram.notify_error("매수 실패", result.get('error'))

        # 7. 통계 출력
        if self.stats['total_trades'] > 0:
            win_rate = self.stats['wins'] / self.stats['total_trades'] * 100
            print(f"\n[통계] 거래: {self.stats['total_trades']}회 | "
                  f"승률: {win_rate:.1f}% | "
                  f"누적 손익: {self.stats['total_pnl']:+.2f}%")

        print("="*80)

    def run(self, interval_seconds: int = 60, summary_interval_hours: int = 6):
        """
        자동매매 무한 루프 실행

        Args:
            interval_seconds: 체크 간격 (초)
            summary_interval_hours: 요약 알림 간격 (시간)
        """
        print(f"\n[자동매매 시작] 체크 간격: {interval_seconds}초")
        print(f"종료: Ctrl+C")

        last_summary_time = datetime.now()
        cycle_count = 0

        while True:
            try:
                self.execute_strategy()

                cycle_count += 1

                # 주기적 요약 알림
                if self.enable_telegram:
                    elapsed = (datetime.now() - last_summary_time).total_seconds()
                    if elapsed >= summary_interval_hours * 3600:
                        positions = self.get_positions()
                        current_pos = positions[0]['symbol'] if positions else None

                        self.telegram.notify_trade_summary(
                            total_trades=self.stats['total_trades'],
                            wins=self.stats['wins'],
                            losses=self.stats['losses'],
                            total_pnl=self.stats['total_pnl'],
                            current_position=current_pos
                        )

                        last_summary_time = datetime.now()

                print(f"\n다음 실행까지 {interval_seconds}초 대기... (사이클: {cycle_count})")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n\n[종료] 사용자가 중단했습니다")
                self.print_final_summary()
                break

            except Exception as e:
                print(f"\n[ERROR] 오류 발생: {e}")
                if self.enable_telegram:
                    self.telegram.notify_error("시스템 오류", str(e))
                import traceback
                traceback.print_exc()
                time.sleep(interval_seconds)

    def print_final_summary(self):
        """최종 요약"""
        print("\n" + "="*80)
        print("최종 거래 요약")
        print("="*80)
        print(f"총 거래 횟수: {self.stats['total_trades']}")
        print(f"승: {self.stats['wins']} | 패: {self.stats['losses']}")

        if self.stats['total_trades'] > 0:
            win_rate = self.stats['wins'] / self.stats['total_trades'] * 100
            print(f"승률: {win_rate:.1f}%")
            print(f"누적 손익: {self.stats['total_pnl']:+.2f}%")

        print("="*80)

        # 최종 요약 텔레그램 알림
        if self.enable_telegram:
            positions = self.get_positions()
            current_pos = positions[0]['symbol'] if positions else None

            self.telegram.notify_trade_summary(
                total_trades=self.stats['total_trades'],
                wins=self.stats['wins'],
                losses=self.stats['losses'],
                total_pnl=self.stats['total_pnl'],
                current_position=current_pos
            )


def main():
    """메인 실행"""
    # 텔레그램 알림 포함 자동매매 시작
    trader = KISAutoTraderWithTelegram(enable_telegram=True)

    # 1회 실행 (테스트)
    # trader.execute_strategy()

    # 자동매매 루프 (실거래용)
    trader.run(interval_seconds=60, summary_interval_hours=6)


if __name__ == "__main__":
    main()
