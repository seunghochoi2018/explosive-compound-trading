#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 포지션 알림 시스템
- 시작 시 최초 포지션 텔레그램 알림
- 포지션 변경 감지 시 텔레그램 알림
- 자동 매매 기능 없음 (알림 전용)
"""

import os
import yaml
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional

class TelegramNotifier:
    """텔레그램 알림 시스템"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """텔레그램 알림 시스템 초기화"""
        # 스크립트 디렉토리 찾기
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # 설정 파일에서 읽거나 기본값 사용
        config_file = os.path.join(script_dir, "telegram_config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.bot_token = config.get('bot_token', bot_token)
                self.chat_id = config.get('chat_id', chat_id)
        else:
            # 기본값
            self.bot_token = bot_token or "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
            self.chat_id = chat_id or "7805944420"

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

        print(f"[텔레그램] 알림 시스템 초기화 완료")
        print(f"  채팅 ID: {self.chat_id}")

    def send_message(self, message: str, disable_notification: bool = False) -> bool:
        """텔레그램 메시지 전송"""
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
        """시작 시 최초 포지션 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if positions:
            # 여러 포지션이 있을 수 있으므로 모두 표시
            position_text = ""
            for i, pos in enumerate(positions, 1):
                position_text += f"""
  {i}. {pos['symbol']}
     - 수량: {pos['qty']:.0f}주
     - 평균가: ${pos['avg_price']:.2f}
     - 현재가: ${pos['current_price']:.2f}
     - 손익: {pos['pnl_pct']:+.2f}%
                """.strip()
                if i < len(positions):
                    position_text += "\n\n"

            message = f"""
 **KIS 포지션 알림 시작**

⏰ **시작 시간**: {timestamp}

 **현재 포지션**:
{position_text}

 **USD 현금**: ${usd_cash:.2f}

 **모니터링 중**
            """.strip()
        else:
            message = f"""
 **KIS 포지션 알림 시작**

⏰ **시작 시간**: {timestamp}

 **현재 포지션**: 없음

 **USD 현금**: ${usd_cash:.2f}

 **모니터링 중**
            """.strip()

        self.send_message(message)

    def notify_position_change(self, change_type: str, positions_before: List[Dict],
                              positions_after: List[Dict], usd_cash: float):
        """포지션 변경 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 이전 포지션
        before_text = "없음"
        if positions_before:
            before_text = ", ".join([f"{p['symbol']} {p['qty']:.0f}주" for p in positions_before])

        # 현재 포지션
        after_text = "없음"
        after_detail = ""
        if positions_after:
            after_text = ", ".join([f"{p['symbol']} {p['qty']:.0f}주" for p in positions_after])
            for pos in positions_after:
                after_detail += f"""
  - {pos['symbol']}: {pos['qty']:.0f}주 @ ${pos['avg_price']:.2f}
    현재가: ${pos['current_price']:.2f} | 손익: {pos['pnl_pct']:+.2f}%
                """.strip()
                after_detail += "\n"

        message = f"""
 **포지션 변경 감지**

⏰ **시간**: {timestamp}

 **변경 내용**:
  - 이전: {before_text}
  - 현재: {after_text}

 **상세 정보**:
{after_detail if after_detail else "  포지션 없음"}

 **USD 현금**: ${usd_cash:.2f}

 **계속 모니터링 중**
        """.strip()

        self.send_message(message)

    def notify_error(self, error_type: str, error_message: str):
        """오류 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = f"""
 **시스템 오류 알림**

⏰ **시간**: {timestamp}

 **오류 유형**: {error_type}

 **내용**: {error_message}
        """.strip()

        self.send_message(message)

    def test_connection(self) -> bool:
        """텔레그램 연결 테스트"""
        try:
            test_message = f" **연결 테스트**\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n KIS 포지션 알림 봇 정상 작동"
            return self.send_message(test_message)
        except Exception as e:
            print(f"[텔레그램] 연결 테스트 실패: {e}")
            return False


class KISPositionMonitor:
    """한국투자증권 포지션 모니터 (알림 전용)"""

    def __init__(self, config_path: str = "kis_devlp.yaml", enable_telegram: bool = True):
        """
        초기화

        Args:
            config_path: 설정 파일 경로
            enable_telegram: 텔레그램 알림 사용 여부
        """
        print("="*80)
        print("한국투자증권 포지션 알림 시스템 v1.0")
        print("="*80)

        # 스크립트 디렉토리 찾기
        script_dir = os.path.dirname(os.path.abspath(__file__))

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

        # 설정 파일 경로를 절대 경로로 변환
        if not os.path.isabs(config_path):
            config_path = os.path.join(script_dir, config_path)

        # 설정 로드
        print(f"[설정 파일] {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 토큰 파일 경로를 절대 경로로 변환
        token_path = os.path.join(script_dir, 'kis_token.json')
        print(f"[토큰 파일] {token_path}")

        # 토큰 로드
        with open(token_path, 'r') as f:
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
        self.currency = "USD"

        # 이전 포지션 저장 (변경 감지용)
        self.previous_positions = []

        print(f"[초기화 완료]")
        print(f"  계좌: {self.cano}-{self.acnt_prdt_cd}")
        print(f"  텔레그램 알림: {'활성화' if self.enable_telegram else '비활성화'}")
        print("="*80)

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
            ord_psbl_frcr_amt = float(output.get('ord_psbl_frcr_amt', '0').replace(',', ''))

            return {
                'success': True,
                'ord_psbl_frcr_amt': ord_psbl_frcr_amt
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

                if qty > 0:
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

    def positions_changed(self, positions_before: List[Dict], positions_after: List[Dict]) -> bool:
        """
        포지션 변경 여부 확인

        Returns:
            변경 여부
        """
        # 포지션 개수가 다르면 변경
        if len(positions_before) != len(positions_after):
            return True

        # 종목과 수량 비교
        before_dict = {p['symbol']: p['qty'] for p in positions_before}
        after_dict = {p['symbol']: p['qty'] for p in positions_after}

        return before_dict != after_dict

    def check_positions(self):
        """포지션 체크 (메인 로직)"""
        print("\n" + "="*80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 포지션 체크")
        print("="*80)

        # USD 현금 잔고 조회
        buying_power = self.get_usd_cash_balance("SOXL", 40.0)

        if not buying_power['success']:
            print(f"[ERROR] USD 현금 조회 실패: {buying_power.get('error')}")
            if self.enable_telegram:
                self.telegram.notify_error("USD 잔고 조회 실패", buying_power.get('error'))
            return

        usd_cash = buying_power['ord_psbl_frcr_amt']

        # 보유 포지션 조회
        current_positions = self.get_positions()

        print(f"\n[계좌 현황]")
        print(f"  USD 현금: ${usd_cash:.2f}")

        if current_positions:
            print(f"  보유 포지션:")
            for pos in current_positions:
                print(f"    - {pos['symbol']}: {pos['qty']:.0f}주 @ ${pos['avg_price']:.2f}")
                print(f"      현재가: ${pos['current_price']:.2f} | 손익: {pos['pnl_pct']:+.2f}%")
        else:
            print(f"  보유 포지션: 없음")

        # 포지션 변경 감지
        if self.previous_positions is not None:
            if self.positions_changed(self.previous_positions, current_positions):
                print("\n[포지션 변경 감지!]")

                if self.enable_telegram:
                    self.telegram.notify_position_change(
                        change_type="CHANGE",
                        positions_before=self.previous_positions,
                        positions_after=current_positions,
                        usd_cash=usd_cash
                    )

        # 현재 포지션 저장
        self.previous_positions = current_positions

        print("="*80)

    def run(self, interval_seconds: int = 30):
        """
        포지션 모니터링 무한 루프

        Args:
            interval_seconds: 체크 간격 (초)
        """
        print(f"\n[모니터링 시작] 체크 간격: {interval_seconds}초")
        print(f"종료: Ctrl+C")

        # 최초 포지션 알림
        if self.enable_telegram:
            buying_power = self.get_usd_cash_balance("SOXL", 40.0)
            if buying_power['success']:
                usd_cash = buying_power['ord_psbl_frcr_amt']
                positions = self.get_positions()
                self.telegram.notify_initial_position(positions, usd_cash)
                self.previous_positions = positions

        cycle_count = 0

        while True:
            try:
                self.check_positions()

                cycle_count += 1

                print(f"\n다음 체크까지 {interval_seconds}초 대기... (사이클: {cycle_count})")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n\n[종료] 사용자가 중단했습니다")
                break

            except Exception as e:
                print(f"\n[ERROR] 오류 발생: {e}")
                if self.enable_telegram:
                    self.telegram.notify_error("시스템 오류", str(e))
                import traceback
                traceback.print_exc()
                time.sleep(interval_seconds)


def main():
    """메인 실행"""
    # 포지션 모니터 시작
    monitor = KISPositionMonitor(enable_telegram=True)

    # 모니터링 루프 (30초마다 체크)
    monitor.run(interval_seconds=30)


if __name__ == "__main__":
    main()
