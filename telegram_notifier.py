#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텔레그램 알림 시스템
- NVDL/NVDQ 포지션 변경 알림
- 거래 신호 및 수익 정보 전송
- 실시간 모니터링 상태 업데이트
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        텔레그램 알림 시스템 초기화

        Args:
            bot_token: 텔레그램 봇 토큰
            chat_id: 대화방 ID
        """
        print("=== 텔레그램 알림 시스템 ===")

        # 기본 설정 (코드3에서 사용된 것과 동일)
        self.bot_token = bot_token or "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
        self.chat_id = chat_id or "7805944420"

        # API URL
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

        # 메시지 템플릿
        self.templates = {
            'position_change': """
 **포지션 변경 알림**

 **이전**: {old_position}
 **신규**: {new_position}

 **신뢰도**: {confidence:.1%}
⏰ **시간**: {timestamp}

 **분석**: {analysis}
            """.strip(),

            'trade_result': """
 **거래 완료**

 **종목**: {symbol}
 **수익률**: {profit_pct:+.2f}%
 **진입가**: ${entry_price:.2f}
 **청산가**: ${exit_price:.2f}

⏱ **보유시간**: {holding_time}
 **결과**: {result}

 **누적 수익**: {total_profit:+.2f}%
 **승률**: {win_rate:.1f}%
            """.strip(),

            'signal_alert': """
 **거래 신호 발생**

 **종목**: {symbol}
[SIGNAL] **신호**: {signal}
 **신뢰도**: {confidence:.1%}

 **현재가**: ${current_price:.2f}
 **기술분석**:
  - RSI: {rsi:.1f}
  - 모멘텀: {momentum:+.2%}
  - 변동성: {volatility:.2%}

⏰ **시간**: {timestamp}
            """.strip(),

            'daily_summary': """
 **일일 거래 요약**

 **날짜**: {date}

 **거래 현황**:
  - 총 거래: {total_trades}회
  - 수익 거래: {winning_trades}회
  - 손실 거래: {losing_trades}회

 **수익 현황**:
  - 일일 수익: {daily_profit:+.2f}%
  - 누적 수익: {total_profit:+.2f}%
  - 승률: {win_rate:.1f}%

 **현재 포지션**: {current_position}

 **시스템 상태**: 정상 운영 중
            """.strip(),

            'error_alert': """
 **시스템 오류 알림**

 **오류 유형**: {error_type}
 **내용**: {error_message}
⏰ **발생 시간**: {timestamp}

 **권장 조치**: {recommendation}
            """.strip(),

            'system_status': """
 **시스템 상태 체크**

 **상태**: {status}
 **가동 시간**: {uptime}
[SIGNAL] **마지막 신호**: {last_signal}

 **포트폴리오**:
  - 현재 포지션: {current_position}
  - 진입 시간: {entry_time}
  - 수익률: {current_pnl:+.2f}%

 **통계**:
  - 총 거래: {total_trades}
  - 승률: {win_rate:.1f}%
  - 누적 수익: {total_profit:+.2f}%

⏰ **업데이트**: {timestamp}
            """.strip()
        }

        # 알림 설정
        self.notification_settings = {
            'position_change': True,    # 포지션 변경 알림
            'trade_result': True,       # 거래 결과 알림
            'signal_alert': True,       # 신호 발생 알림
            'daily_summary': True,      # 일일 요약
            'error_alert': True,        # 오류 알림
            'system_status': False,     # 주기적 상태 체크 (기본 off)
            'hourly_update': False      # 시간당 업데이트 (기본 off)
        }

        # 최근 메시지 추적 (중복 방지)
        self.recent_messages = []
        self.max_recent_messages = 50

        # 일반 상태 알림 시간 제한 (6시간)
        self.last_routine_notification_time = 0
        self.routine_notification_interval = 6 * 3600  # 6시간

        print(f"봇 토큰: {self.bot_token[:20]}...")
        print(f"채팅 ID: {self.chat_id}")
        print("설정된 알림 유형:", [k for k, v in self.notification_settings.items() if v])
        print("일반 알림 주기: 6시간")

    def send_message(self, message: str, disable_notification: bool = False, priority: str = "important") -> bool:
        """
        텔레그램 메시지 전송

        Args:
            message: 전송할 메시지
            disable_notification: 무음 알림 여부
            priority: 메시지 우선순위
                - "routine": 일반 상태 알림 (6시간마다만 전송)
                - "important": 거래/이슈 알림 (항상 전송)
                - "emergency": 긴급 알림 (항상 전송)

        Returns:
            전송 성공 여부
        """
        try:
            # 우선순위 체크
            current_time = time.time()
            if priority == "routine":
                # 일반 알림은 6시간마다만 전송
                if current_time - self.last_routine_notification_time < self.routine_notification_interval:
                    print(f"[텔레그램] 일반 알림 생략 (다음 전송까지: {(self.routine_notification_interval - (current_time - self.last_routine_notification_time))/3600:.1f}시간)")
                    return True
                self.last_routine_notification_time = current_time

            # 중복 메시지 체크 (긴급 알림은 중복 체크 안 함)
            if priority != "emergency" and message in self.recent_messages:
                return True

            url = f"{self.api_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_notification': disable_notification
            }

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            # 성공 시 최근 메시지에 추가
            self.recent_messages.append(message)
            if len(self.recent_messages) > self.max_recent_messages:
                self.recent_messages.pop(0)

            return True

        except Exception as e:
            print(f"텔레그램 메시지 전송 오류: {e}")
            return False

    def notify_position_change(self, old_position: str, new_position: str,
                             confidence: float, analysis: str = "") -> bool:
        """포지션 변경 알림"""
        if not self.notification_settings['position_change']:
            return True

        message = self.templates['position_change'].format(
            old_position=old_position or "없음",
            new_position=new_position or "없음",
            confidence=confidence,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            analysis=analysis or "AI 모델 기반 추천"
        )

        return self.send_message(message)

    def notify_trade_result(self, symbol: str, profit_pct: float, entry_price: float,
                          exit_price: float, holding_time: str, total_profit: float,
                          win_rate: float) -> bool:
        """거래 결과 알림"""
        if not self.notification_settings['trade_result']:
            return True

        result = " 수익" if profit_pct > 0 else " 손실"

        message = self.templates['trade_result'].format(
            symbol=symbol,
            profit_pct=profit_pct,
            entry_price=entry_price,
            exit_price=exit_price,
            holding_time=holding_time,
            result=result,
            total_profit=total_profit,
            win_rate=win_rate
        )

        return self.send_message(message)

    def notify_signal_alert(self, symbol: str, signal: str, confidence: float,
                          current_price: float, rsi: float = 50, momentum: float = 0,
                          volatility: float = 0) -> bool:
        """거래 신호 알림"""
        if not self.notification_settings['signal_alert']:
            return True

        message = self.templates['signal_alert'].format(
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            current_price=current_price,
            rsi=rsi,
            momentum=momentum,
            volatility=volatility,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        return self.send_message(message)

    def notify_daily_summary(self, total_trades: int, winning_trades: int,
                           daily_profit: float, total_profit: float, win_rate: float,
                           current_position: str = "없음") -> bool:
        """일일 요약 알림"""
        if not self.notification_settings['daily_summary']:
            return True

        losing_trades = total_trades - winning_trades

        message = self.templates['daily_summary'].format(
            date=datetime.now().strftime('%Y-%m-%d'),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            daily_profit=daily_profit,
            total_profit=total_profit,
            win_rate=win_rate,
            current_position=current_position
        )

        return self.send_message(message, disable_notification=True)

    def notify_error(self, error_type: str, error_message: str,
                    recommendation: str = "시스템 관리자에게 문의하세요") -> bool:
        """오류 알림"""
        if not self.notification_settings['error_alert']:
            return True

        message = self.templates['error_alert'].format(
            error_type=error_type,
            error_message=error_message,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            recommendation=recommendation
        )

        return self.send_message(message)

    def notify_system_status(self, status: str, uptime: str, last_signal: str,
                           current_position: str, entry_time: str, current_pnl: float,
                           total_trades: int, win_rate: float, total_profit: float) -> bool:
        """시스템 상태 알림"""
        if not self.notification_settings['system_status']:
            return True

        message = self.templates['system_status'].format(
            status=status,
            uptime=uptime,
            last_signal=last_signal,
            current_position=current_position,
            entry_time=entry_time,
            current_pnl=current_pnl,
            total_trades=total_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        return self.send_message(message, disable_notification=True)

    def test_connection(self) -> bool:
        """텔레그램 연결 테스트"""
        try:
            test_message = f" **연결 테스트**\n\n⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n NVDL/NVDQ 알림 봇이 정상 작동 중입니다."
            return self.send_message(test_message)
        except Exception as e:
            print(f"텔레그램 연결 테스트 실패: {e}")
            return False

    def set_notification_settings(self, **settings):
        """알림 설정 변경"""
        for key, value in settings.items():
            if key in self.notification_settings:
                self.notification_settings[key] = value
                print(f"알림 설정 변경: {key} = {value}")

    def get_chat_info(self) -> Optional[Dict]:
        """채팅방 정보 조회"""
        try:
            url = f"{self.api_url}/getChat"
            data = {'chat_id': self.chat_id}

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                return result.get('result')
            else:
                print(f"채팅방 정보 조회 실패: {result}")
                return None

        except Exception as e:
            print(f"채팅방 정보 조회 오류: {e}")
            return None

    def format_currency(self, amount: float) -> str:
        """통화 포맷팅"""
        if abs(amount) >= 1000000:
            return f"${amount/1000000:.2f}M"
        elif abs(amount) >= 1000:
            return f"${amount/1000:.2f}K"
        else:
            return f"${amount:.2f}"

    def format_percentage(self, value: float) -> str:
        """퍼센트 포맷팅"""
        if value >= 0:
            return f"+{value:.2f}%"
        else:
            return f"{value:.2f}%"

    def format_time_duration(self, start_time: datetime) -> str:
        """시간 간격 포맷팅"""
        if start_time is None:
            return "알 수 없음"

        delta = datetime.now() - start_time
        total_seconds = int(delta.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}시간 {minutes}분"
        else:
            return f"{minutes}분"

def main():
    """테스트 실행"""
    print("텔레그램 알림 시스템 테스트")

    # 알림 시스템 생성
    notifier = TelegramNotifier()

    # 연결 테스트
    print("연결 테스트 중...")
    if notifier.test_connection():
        print(" 텔레그램 연결 성공!")
    else:
        print(" 텔레그램 연결 실패!")
        return

    # 각종 알림 테스트
    print("\n알림 테스트 시작...")

    # 1. 포지션 변경 알림
    notifier.notify_position_change(
        old_position="없음",
        new_position="NVDL",
        confidence=0.75,
        analysis="강한 상승 모멘텀 감지"
    )

    time.sleep(2)

    # 2. 거래 신호 알림
    notifier.notify_signal_alert(
        symbol="NVDL",
        signal="매수",
        confidence=0.68,
        current_price=45.32,
        rsi=65.4,
        momentum=0.025,
        volatility=0.032
    )

    time.sleep(2)

    # 3. 거래 결과 알림
    notifier.notify_trade_result(
        symbol="NVDQ",
        profit_pct=2.8,
        entry_price=18.45,
        exit_price=18.97,
        holding_time="3시간 15분",
        total_profit=15.6,
        win_rate=72.3
    )

    time.sleep(2)

    # 4. 일일 요약
    notifier.notify_daily_summary(
        total_trades=8,
        winning_trades=6,
        daily_profit=4.2,
        total_profit=15.6,
        win_rate=75.0,
        current_position="NVDL"
    )

    print(" 모든 테스트 완료!")

if __name__ == "__main__":
    main()