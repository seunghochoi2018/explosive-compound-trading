#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텔레그램 알림 및 Ollama 자동 시작 헬퍼
"""

import os
import json
import time
import requests
import subprocess
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None


def start_ollama():
    """Ollama 11435 포트로 자동 시작"""
    print("\n" + "="*80)
    print("Ollama 서버 확인 및 시작")
    print("="*80)

    # 기존 Ollama 프로세스 종료
    if psutil:
        print("기존 Ollama 프로세스 확인 중...")
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                    print(f"  종료: {proc.info['name']} (PID: {proc.pid})")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(2)
    else:
        print("psutil 없음 - 기존 프로세스 확인 생략")

    # Ollama 11435 포트로 시작
    ollama_path = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"
    models_path = r"C:\Users\user\.ollama\models"

    print(f"\nOllama 시작 중...")
    print(f"  경로: {ollama_path}")
    print(f"  포트: 11435")
    print(f"  모델 경로: {models_path}")

    # 환경변수 설정
    env = os.environ.copy()
    env['OLLAMA_HOST'] = '127.0.0.1:11435'
    env['OLLAMA_MODELS'] = models_path

    # 백그라운드로 실행
    try:
        subprocess.Popen(
            [ollama_path, 'serve'],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print("  [OK] Ollama 시작 완료")
    except Exception as e:
        print(f"  [ERROR] Ollama 시작 실패: {e}")
        print("  수동으로 start_ollama_11435.bat을 실행하세요")
        return False

    # 서버 준비 대기
    print("\nOllama 서버 준비 대기 중...")
    for i in range(10):
        try:
            response = requests.get("http://127.0.0.1:11435/api/tags", timeout=2)
            if response.status_code == 200:
                result = response.json()
                models = result.get('models', [])
                print(f"  [OK] Ollama 서버 준비 완료")
                print(f"  모델 개수: {len(models)}")
                return True
        except Exception as e:
            pass
        print(f"  대기 중... ({i+1}/10)")
        time.sleep(2)

    print("  [WARNING] Ollama 서버 응답 없음 (계속 진행)")
    return True


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
            emoji = "🟢"
            action_text = "매수 신호"
        elif action == 'SELL':
            emoji = "🔴"
            action_text = "매도 신호"
        else:
            emoji = "🔵"
            action_text = action

        position_info = ""
        if current_position:
            position_info = f"\n\n💼 **현재 포지션**: {current_position} (손익 {current_pnl_pct:+.2f}%)"

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
