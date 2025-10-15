#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from datetime import datetime

def send_emergency_telegram():
    """긴급 상황 텔레그램 알림"""
    
    # 텔레그램 설정
    BOT_TOKEN = "7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
    CHAT_ID = "7123456789"
    
    # 현재 시간
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 긴급 메시지
    message = f"""
🚨 <b>긴급 상황 알림</b> 🚨

<b>시스템 재구축 실패</b>
• 시간: {current_time}
• 문제: Ollama 포트 연결 실패
• 포트: 11434, 11435, 11436, 11437 모두 비활성화

<b>수동 조치 필요</b>
1. Ollama 재설치 확인
2. 포트 충돌 확인  
3. 방화벽 설정 확인
4. 관리자 권한으로 재시작

<b>현재 상태</b>
• 통합 매니저: 중단됨
• 이더 트레이더: 중단됨  
• KIS 트레이더: 중단됨
• 모든 거래: 중단됨

<b>즉시 조치 필요!</b>
"""
    
    # 텔레그램 API 호출
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[{current_time}] 긴급 텔레그램 알림 발송 성공")
            return True
        else:
            print(f"[{current_time}] 텔레그램 알림 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"[{current_time}] 텔레그램 알림 오류: {e}")
        return False

if __name__ == "__main__":
    send_emergency_telegram()

