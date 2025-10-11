#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 동적 스케줄러
- RTX 2060 6GB 최적화
- 7b 3개 교대 사용
- Lock 기반 순차 처리
"""
import threading
import time
import requests
from datetime import datetime

class GPUScheduler:
    """GPU 메모리 동적 관리"""

    def __init__(self):
        self.lock = threading.Lock()
        self.current_user = None
        self.ollama_ports = {
            'ETH': 11434,
            'KIS': 11435,
            'MANAGER': 11436
        }

    def request_gpu(self, trader_name: str, model_name: str, timeout: int = 60):
        """
        GPU 사용 요청

        Args:
            trader_name: 'ETH', 'KIS', 'MANAGER'
            model_name: 'qwen2.5:7b' or 'qwen2.5:14b'
            timeout: 최대 대기 시간 (초)

        Returns:
            bool: GPU 획득 성공 여부
        """
        acquired = self.lock.acquire(timeout=timeout)

        if acquired:
            self.current_user = trader_name
            print(f"[GPU] {trader_name}가 {model_name} 사용 시작 ({datetime.now().strftime('%H:%M:%S')})")
            return True
        else:
            print(f"[GPU] {trader_name} 대기 타임아웃 (현재 사용자: {self.current_user})")
            return False

    def release_gpu(self, trader_name: str, model_name: str, port: int):
        """
        GPU 해제 및 모델 언로드

        Args:
            trader_name: 'ETH', 'KIS', 'MANAGER'
            model_name: 'qwen2.5:7b' or 'qwen2.5:14b'
            port: Ollama 포트
        """
        try:
            # Ollama 모델 즉시 언로드
            url = f"http://127.0.0.1:{port}/api/generate"
            data = {
                "model": model_name,
                "prompt": "",
                "keep_alive": 0  # 즉시 언로드
            }
            requests.post(url, json=data, timeout=5)
            print(f"[GPU] {trader_name}의 {model_name} 언로드 완료")
        except Exception as e:
            print(f"[GPU] 모델 언로드 실패: {e}")
        finally:
            self.current_user = None
            self.lock.release()
            print(f"[GPU] {trader_name}가 GPU 반납 ({datetime.now().strftime('%H:%M:%S')})")

    def get_status(self):
        """현재 GPU 상태"""
        if self.lock.locked():
            return f"사용 중: {self.current_user}"
        else:
            return "대기 중"

# 전역 스케줄러 인스턴스
gpu_scheduler = GPUScheduler()
