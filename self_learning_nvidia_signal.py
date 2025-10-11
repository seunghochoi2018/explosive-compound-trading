#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자가학습 NVIDIA 신호 시스템
- 신호 정확도로부터 학습
- 가중치 자동 조정으로 신호 품질 향상
- 시간이 지날수록 정확도 향상
"""

import json
import time
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import deque
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

class LearningSignalDatabase:
    """학습 신호 데이터베이스"""

    def __init__(self):
        self.db_path = "nvidia_signals_learning.db"
        self.init_database()

    def init_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            signal_type TEXT,
            confidence REAL,
            price REAL,
            rsi REAL,
            price_change REAL,
            actual_outcome TEXT,
            profit_rate REAL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            weights TEXT,
            accuracy_rate REAL
        )
        ''')

        conn.commit()
        conn.close()

    def save_signal(self, signal_data: Dict):
        """신호 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO signal_history (timestamp, symbol, signal_type, confidence,
                                   price, rsi, price_change, actual_outcome, profit_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_data['timestamp'],
            signal_data['symbol'],
            signal_data['signal_type'],
            signal_data['confidence'],
            signal_data['price'],
            signal_data['rsi'],
            signal_data['price_change'],
            signal_data.get('actual_outcome', ''),
            signal_data.get('profit_rate', 0)
        ))

        conn.commit()
        conn.close()

    def update_signal_outcome(self, signal_id: int, outcome: str, profit_rate: float):
        """신호 결과 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        UPDATE signal_history
        SET actual_outcome = ?, profit_rate = ?
        WHERE id = ?
        ''', (outcome, profit_rate, signal_id))

        conn.commit()
        conn.close()

    def get_recent_signals(self, days: int = 7) -> List[Dict]:
        """최근 신호 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute('''
        SELECT * FROM signal_history
        WHERE timestamp > ?
        ORDER BY timestamp DESC
        ''', (cutoff_date,))

        signals = []
        for row in cursor.fetchall():
            signals.append({
                'id': row[0],
                'timestamp': row[1],
                'symbol': row[2],
                'signal_type': row[3],
                'confidence': row[4],
                'price': row[5],
                'rsi': row[6],
                'price_change': row[7],
                'actual_outcome': row[8],
                'profit_rate': row[9]
            })

        conn.close()
        return signals

class SelfLearningNVIDIASignal:
    """자가학습 NVIDIA 신호 시스템"""

    def __init__(self):
        # API 설정
        self.fmp_api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

        # 텔레그램 설정
        self.telegram_token = "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
        self.chat_id = "7805944420"

        # LLM 설정
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "qwen2.5:1.5b"  # 빠른 모델

        # 학습 가능한 가중치
        self.weights = {
            'price_momentum': 1.0,
            'rsi_signal': 1.0,
            'volume_factor': 1.0,
            'volatility_importance': 1.0,
            'llm_trust': 1.0,
            'nvdl_bias': 1.0,  # NVDL 선호도
            'nvdd_bias': 1.0   # NVDD 선호도
        }

        # 데이터베이스
        self.db = LearningSignalDatabase()

        # 성과 추적
        self.signal_accuracy = deque(maxlen=50)
        self.learning_rate = 0.01

        # 설정
        self.config = {
            'check_interval': 300,      # 5분
            'min_confidence': 0.6,      # 동적 조정됨
            'cooldown_period': 1800,    # 30분
        }

        # 상태
        self.last_signals = {}
        self.pending_signals = {}  # 결과 확인 대기 중인 신호

        self.load_weights()

        logger.info(" 자가학습 NVIDIA 신호 시스템 초기화 완료")

    def load_weights(self):
        """가중치 로드"""
        try:
            with open('nvidia_learning_weights.json', 'r') as f:
                data = json.load(f)
                self.weights = data.get('weights', self.weights)
                accuracy = data.get('accuracy_rate', 0)
                logger.info(f" 학습된 가중치 로드 (정확도: {accuracy:.1%})")
        except FileNotFoundError:
            logger.info("🆕 새로운 학습 시작")

    def save_weights(self):
        """가중치 저장"""
        accuracy = np.mean(self.signal_accuracy) if self.signal_accuracy else 0.5

        with open('nvidia_learning_weights.json', 'w') as f:
            json.dump({
                'weights': self.weights,
                'accuracy_rate': accuracy,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

    def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """주식 데이터 조회"""
        try:
            # 현재 가격
            price_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
            price_params = {"apikey": self.fmp_api_key}

            price_response = requests.get(price_url, params=price_params, timeout=10)
            if price_response.status_code != 200:
                return None

            price_data = price_response.json()
            if not price_data:
                return None

            current_price = price_data[0]["price"]
            change_percent = price_data[0]["changesPercentage"]
            volume = price_data[0]["volume"]

            # RSI 계산 (간단)
            rsi = 50  # 기본값
            if change_percent > 3:
                rsi = 70 + min(change_percent, 30)
            elif change_percent < -3:
                rsi = 30 - min(abs(change_percent), 30)
            else:
                rsi = 50 + (change_percent * 5)

            return {
                "symbol": symbol,
                "price": current_price,
                "change_percent": change_percent,
                "volume": volume,
                "rsi": rsi,
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error(f" {symbol} 데이터 조회 실패: {e}")
            return None

    def adaptive_signal_generation(self, nvdl_data: Dict, nvdd_data: Dict) -> Tuple[Optional[Dict], Optional[Dict]]:
        """적응형 신호 생성 (학습된 가중치 사용)"""

        signals = []

        for symbol, data in [("NVDL", nvdl_data), ("NVDD", nvdd_data)]:
            if not data:
                continue

            # 학습된 가중치로 점수 계산
            score = 0.0

            # 가격 모멘텀
            momentum = data['change_percent'] / 10.0  # 정규화
            score += momentum * self.weights['price_momentum']

            # RSI 신호
            rsi = data['rsi']
            if symbol == "NVDL":
                if rsi < 30:  # NVDL 과매도 - 매수 기회
                    score += 0.5 * self.weights['rsi_signal'] * self.weights['nvdl_bias']
                elif rsi > 70:  # NVDL 과매수 - 매도 신호
                    score -= 0.5 * self.weights['rsi_signal'] * self.weights['nvdl_bias']
            else:  # NVDD
                if rsi < 30:  # NVDD 과매도 (NVIDIA 상승) - 매수 기회
                    score += 0.5 * self.weights['rsi_signal'] * self.weights['nvdd_bias']
                elif rsi > 70:  # NVDD 과매수 (NVIDIA 하락) - 매도 신호
                    score -= 0.5 * self.weights['rsi_signal'] * self.weights['nvdd_bias']

            # LLM 분석 (빠른 결정)
            llm_signal = self._quick_llm_analysis(data)
            score += llm_signal * self.weights['llm_trust']

            # 최종 신뢰도 계산
            confidence = abs(score) / 3.0  # 정규화
            confidence = min(0.95, confidence)

            # 동적 최소 신뢰도 (학습 기반 조정)
            accuracy = np.mean(self.signal_accuracy) if self.signal_accuracy else 0.5
            dynamic_min_confidence = self.config['min_confidence'] * (2 - accuracy)  # 정확도 낮으면 더 보수적

            if confidence >= dynamic_min_confidence:
                signal_type = "BUY" if score > 0 else "SELL" if score < 0 else "HOLD"

                if signal_type != "HOLD":
                    signal = {
                        'symbol': symbol,
                        'signal_type': signal_type,
                        'confidence': confidence,
                        'price': data['price'],
                        'change_percent': data['change_percent'],
                        'rsi': rsi,
                        'score': score
                    }
                    signals.append(signal)

        return signals

    def _quick_llm_analysis(self, data: Dict) -> float:
        """빠른 LLM 분석"""
        try:
            prompt = f"{data['symbol']}: ${data['price']:.2f} ({data['change_percent']:+.2f}%) RSI:{data['rsi']:.0f} BUY/SELL/HOLD?"

            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '').upper()

                if 'BUY' in text:
                    return 0.3
                elif 'SELL' in text:
                    return -0.3
                else:
                    return 0
            return 0

        except:
            return 0

    def update_weights_from_outcome(self, signal: Dict, actual_profit: float):
        """결과로부터 가중치 학습"""

        # 성과 평가
        success = actual_profit > 0
        self.signal_accuracy.append(1 if success else 0)

        # 가중치 업데이트
        learning_factor = self.learning_rate * abs(actual_profit)

        if success:
            # 성공한 조건의 가중치 강화
            if abs(signal['change_percent']) > 3:
                self.weights['price_momentum'] += learning_factor

            if signal['rsi'] < 30 or signal['rsi'] > 70:
                self.weights['rsi_signal'] += learning_factor

            if signal['symbol'] == "NVDL":
                self.weights['nvdl_bias'] += learning_factor
            else:
                self.weights['nvdd_bias'] += learning_factor
        else:
            # 실패한 조건의 가중치 약화
            if abs(signal['change_percent']) > 3:
                self.weights['price_momentum'] -= learning_factor

            if signal['rsi'] < 30 or signal['rsi'] > 70:
                self.weights['rsi_signal'] -= learning_factor

        # 가중치 정규화 (0.1 ~ 3.0)
        for key in self.weights:
            self.weights[key] = max(0.1, min(3.0, self.weights[key]))

        self.save_weights()

        accuracy = np.mean(self.signal_accuracy) if self.signal_accuracy else 0.5
        logger.info(f" 학습 완료 - 정확도: {accuracy:.1%}")

    def send_telegram(self, message: str) -> bool:
        """텔레그램 전송"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f" 텔레그램 전송 실패: {e}")
            return False

    def check_pending_signals(self):
        """대기 중인 신호 결과 확인 (30분 후)"""
        current_time = datetime.now()

        for signal_id, signal_data in list(self.pending_signals.items()):
            signal_time = signal_data['timestamp']

            # 30분 경과 확인
            if (current_time - signal_time).seconds >= 1800:
                # 현재 가격으로 결과 계산
                current_data = self.get_stock_data(signal_data['symbol'])

                if current_data:
                    if signal_data['signal_type'] == 'BUY':
                        profit_rate = (current_data['price'] - signal_data['price']) / signal_data['price']
                    else:  # SELL
                        profit_rate = (signal_data['price'] - current_data['price']) / signal_data['price']

                    # 학습
                    self.update_weights_from_outcome(signal_data, profit_rate)

                    # 데이터베이스 업데이트
                    self.db.update_signal_outcome(
                        signal_id,
                        "SUCCESS" if profit_rate > 0 else "FAIL",
                        profit_rate
                    )

                    # 결과 알림
                    result_msg = f" 신호 결과 - {signal_data['symbol']}\n"
                    result_msg += f"수익률: {profit_rate:+.2%}\n"
                    result_msg += f"정확도: {np.mean(self.signal_accuracy):.1%}"
                    self.send_telegram(result_msg)

                # 대기 목록에서 제거
                del self.pending_signals[signal_id]

    def run_analysis_cycle(self):
        """분석 사이클 실행"""
        logger.info(f"\n⏰ 시장 분석 중... ({datetime.now().strftime('%H:%M:%S')})")

        # 데이터 수집
        nvdl_data = self.get_stock_data("NVDL")
        nvdd_data = self.get_stock_data("NVDD")

        if not nvdl_data or not nvdd_data:
            logger.error(" 가격 데이터 수집 실패")
            return

        logger.info(f"NVDL: ${nvdl_data['price']:.2f} ({nvdl_data['change_percent']:+.2f}%)")
        logger.info(f"NVDD: ${nvdd_data['price']:.2f} ({nvdd_data['change_percent']:+.2f}%)")

        # 적응형 신호 생성
        signals = self.adaptive_signal_generation(nvdl_data, nvdd_data)

        for signal in signals:
            # 쿨다운 체크
            symbol = signal['symbol']
            if symbol in self.last_signals:
                last_time = self.last_signals[symbol]['timestamp']
                if (datetime.now() - last_time).seconds < self.config['cooldown_period']:
                    logger.info(f"⏸ {symbol} 쿨다운 중")
                    continue

            # 신호 전송
            message = f" **{signal['symbol']} {signal['signal_type']} 신호**\n\n"
            message += f" 가격: ${signal['price']:.2f}\n"
            message += f" 변화율: {signal['change_percent']:+.2f}%\n"
            message += f" RSI: {signal['rsi']:.1f}\n"
            message += f" 신뢰도: {signal['confidence']:.1%}\n"
            message += f" 현재 정확도: {np.mean(self.signal_accuracy):.1%}" if self.signal_accuracy else ""

            if self.send_telegram(message):
                logger.info(f" {signal['symbol']} 신호 전송 완료")

                # 신호 저장
                signal_data = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': signal['symbol'],
                    'signal_type': signal['signal_type'],
                    'confidence': signal['confidence'],
                    'price': signal['price'],
                    'rsi': signal['rsi'],
                    'price_change': signal['change_percent'],
                    'actual_outcome': '',
                    'profit_rate': 0
                }
                self.db.save_signal(signal_data)

                # 대기 목록에 추가 (결과 추적용)
                recent_signals = self.db.get_recent_signals(1)
                if recent_signals:
                    signal_id = recent_signals[0]['id']
                    self.pending_signals[signal_id] = {
                        **signal,
                        'timestamp': datetime.now()
                    }

                # 마지막 신호 업데이트
                self.last_signals[symbol] = {
                    'timestamp': datetime.now(),
                    'signal_type': signal['signal_type']
                }

        # 대기 중인 신호 결과 확인
        self.check_pending_signals()

    def run(self):
        """메인 실행 루프"""
        logger.info(" 자가학습 NVIDIA 신호 시스템 시작")
        logger.info(f" 체크 간격: {self.config['check_interval']//60}분")
        logger.info(f" 최소 신뢰도: {self.config['min_confidence']:.1%} (동적 조정)")
        logger.info("=" * 60)

        while True:
            try:
                self.run_analysis_cycle()

                logger.info(f"⏰ {self.config['check_interval']//60}분 대기 중...")
                time.sleep(self.config['check_interval'])

            except KeyboardInterrupt:
                logger.info("\n 사용자 중단 - 프로그램 종료")
                break
            except Exception as e:
                logger.error(f" 시스템 오류: {e}")
                logger.info(" 1분 후 재시도...")
                time.sleep(60)

if __name__ == "__main__":
    signal_system = SelfLearningNVIDIASignal()
    signal_system.run()