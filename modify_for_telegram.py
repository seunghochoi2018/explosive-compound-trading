#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kis_llm_trader.py를 텔레그램 알림 버전으로 자동 수정
"""

import re

# 1. 원본 파일 읽기
with open('kis_llm_learner_with_telegram.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 2. 텔레그램 클래스 추가 (import 섹션 다음에)
telegram_class = '''

# ============================================================================
# 텔레그램 알림 시스템
# ============================================================================

class TelegramNotifier:
    """텔레그램 알림 시스템"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """텔레그램 알림 시스템 초기화"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, "telegram_config.json")

        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.bot_token = config.get('bot_token', bot_token)
                self.chat_id = config.get('chat_id', chat_id)
        else:
            self.bot_token = bot_token or "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
            self.chat_id = chat_id or "7805944420"

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

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
            print(f"[텔레그램 오류] {e}")
            return False

    def notify_trading_signal(self, action: str, symbol: str, quantity: int,
                             reasoning: str, confidence: float = 0,
                             current_position: str = None, current_pnl_pct: float = 0):
        """매매 신호 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if action == 'BUY':
            emoji = ""
            action_text = "매수 신호"
        elif action == 'SELL':
            emoji = ""
            action_text = "매도 신호"
        else:
            emoji = ""
            action_text = action

        position_info = ""
        if current_position:
            position_info = f"\\n\\n **현재 포지션**: {current_position} (손익 {current_pnl_pct:+.2f}%)"

        message = f"""
{emoji} **LLM 매매 신호**

⏰ **시간**: {timestamp}

 **신호**: {action_text}
 **종목**: {symbol}
 **수량**: {quantity}주
 **신뢰도**: {confidence:.0f}%

 **분석 근거**:
{reasoning}{position_info}

 **실제 거래는 직접 하세요!**
        """.strip()

        self.send_message(message)

    def notify_position_change(self, old_pos: str, new_pos: str, pnl_pct: float):
        """포지션 변경 감지 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result = " 수익" if pnl_pct > 0 else " 손실"

        message = f"""
 **포지션 변경 감지!**

⏰ **시간**: {timestamp}

 **변경 내용**:
  - 이전: {old_pos or '없음'}
  - 현재: {new_pos or '없음'}

 **손익**: {result} {pnl_pct:+.2f}%

 자동으로 학습 데이터에 기록됩니다.
        """.strip()

        self.send_message(message)

'''

# import 섹션 찾기
import_end = content.find('class KISLLMTrader:')
if import_end == -1:
    import_end = content.find('def ')

# 텔레그램 클래스 삽입
content = content[:import_end] + telegram_class + '\\n\\n' + content[import_end:]

# 3. KISLLMTrader __init__에 텔레그램 초기화 추가
# "# 통계" 섹션 찾기
stats_section = content.find("# 통계")
if stats_section != -1:
    telegram_init = '''

        # 텔레그램 알림
        try:
            self.telegram = TelegramNotifier()
            print("[텔레그램] 알림 시스템 활성화")
            self.enable_telegram = True
        except Exception as e:
            print(f"[경고] 텔레그램 초기화 실패: {e}")
            self.enable_telegram = False

        # 포지션 추적 (학습 데이터 자동 기록용)
        self.last_known_position = None
        self.position_entry_time = None
        self.position_entry_price = None
'''
    # stats_section 위치에 삽입
    content = content[:stats_section] + telegram_init + '\\n        ' + content[stats_section:]

# 4. place_order 함수를 텔레그램 알림으로 교체
place_order_pattern = r'def place_order\(self.*?\n(?:.*?\n)*?.*?return \{\'success\': False.*?\}'
place_order_replacement = '''def place_order(self, symbol: str, order_type: str, quantity: int = None, price: float = None) -> Dict:
        """
        주문 시뮬레이션 (텔레그램 알림만, 실제 주문 안 함)
        """
        print(f"\\n[주문 시뮬레이션] {order_type} {symbol} {quantity}주")

        # 텔레그램 알림
        if self.enable_telegram:
            self.telegram.notify_trading_signal(
                action=order_type,
                symbol=symbol,
                quantity=quantity or 0,
                reasoning="14b × 2 LLM 분석 결과",
                confidence=75
            )

        # 시뮬레이션 성공
        return {
            'success': True,
            'order_no': 'SIM_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'message': '시뮬레이션 (텔레그램 알림 전송)',
            'quantity': quantity or 0
        }'''

content = re.sub(place_order_pattern, place_order_replacement, content, flags=re.DOTALL)

# 5. 저장
with open('kis_llm_learner_with_telegram.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] 수정 완료: kis_llm_learner_with_telegram.py")
print("   - 텔레그램 클래스 추가")
print("   - 텔레그램 초기화 추가")
print("   - place_order 함수 교체")
