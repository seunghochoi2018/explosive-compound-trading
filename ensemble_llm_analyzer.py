#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 LLM  - 14b × 4  

===   (RAM 28GB ) ===
14b × 4 = 4  (96 )
- Layer 1-24 (14b × 1):   (1, 7GB)
- Layer 25-48 (14b × 1): ~  (5~30, 7GB)
- Layer 49-72 (14b × 1):   (1, 7GB)
- Layer 73-96 (14b × 1):   ( , 7GB)

===    ( ) ===

1.   (93% )
   -  : 150 → 20  (L{range}:{decision}({conf}%))
   -  : 1 10→5, 5 20→8,  50→10
   -  :  (41,315 chars → 2,000 chars)

2. RAM   (40GB  28GB )
   - 14b: num_ctx=32768, num_batch=8192 (7GB × 4 = 28GB)
   -  : use_mmap=True, use_mlock=True ( )

3.   
   - 14b: num_predict=250 ( )
   -  : stop=["\n\n", "```", "##", "}"]

4.   
   - top_k: 40→5 (  87% )
   - top_p: 0.9→0.3 (  66% )
   - tfs_z: 1.0→0.5 (Tail Free Sampling)
   - typical_p: 0.7 (Typical Sampling)

5.   
   - repeat_penalty=1.0 (  )
   - presence_penalty=0.0 (  )
   - frequency_penalty=0.0 (  )
   - penalize_newline=False (  )
   - mirostat=0 (Mirostat  )

6. GPU/CPU 
   - num_gpu=99 ( GPU  )
   - main_gpu=0 ( GPU )
   - num_thread: 1.5b=8, 14b=12 ( )
   - num_parallel=4 (14b 2  )
   - numa=True (NUMA )

7.  
   - f16_kv=True (FP16 KV ,  2)
   - low_vram=False (VRAM  )
   - num_keep=4 ( )
   - logits_all=False (   )

8.   
   - keep_alive=60m (60 RAM )
   -       ( )

===   ===
- 14b × 2 + 1.5b × 1 = 3 
-  : 14b(118) × 2 + 1.5b(10) =  250 (4)
-  : 180 (3)

 :        ( )
 : Layer 65-96 (14b)  
"""

import json
import requests
import time
from typing import Dict, List, Optional
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class EnsembleLLMAnalyzer:
    """13 LLM    ( +  )"""

    def __init__(self, base_model="qwen2.5:14b"):
        self.base_model = base_model
        self.power_model = base_model  # [FIX] base_model 파라미터 사용
        self.ollama_url = "http://localhost:11435"  # KIS 전용 Ollama 서버

        print("[MAX_PERFORMANCE] 14b × 2   ")
        print("[MAX_PERFORMANCE] RAM 14GB  (7GB )")
        print("[MAX_PERFORMANCE]   : 4")
        # self._preload_models()  # [DISABLED] 멈춤 현상으로 비활성화
        print("[INFO] _preload_models() 건너뜀")

        # 2    (14b × 2)
        # [FIX] base_model 파라미터 사용 (하드코딩 제거)
        self.models = {
            "layer_1_48": {  # Layer 1-48:  +
                "role": f" / ({base_model})",
                "focus": "1~15 ,  +",
                "timeframe": "1m-15m",
                "temperature": 0.10,
                "layer_emulation": "1-48",
                "model": base_model
            },
            "layer_49_96": {  # Layer 49-96:  +
                "role": f" / ({base_model})",
                "focus": " ,  +",
                "timeframe": "all",
                "temperature": 0.30,
                "layer_emulation": "49-96",
                "model": base_model
            }
        }

        print(f"[ENSEMBLE] 1 LLM (14b × 1)   ")
        print(f"  - Layer 49-96: {self.power_model} ( +)")
        print(f"  - : ~7GB (14b:7GB × 1)")
        print(f"  - :  45 ")

    def analyze_sequential(self, market_data: Dict, trade_history: List[Dict],
                          meta_insights: List[Dict]) -> Dict:
        """
        3    (14b × 3 = 96 14b )

        Layer 1-32 → 33-64 → 65-96
               ( )

        Returns:
            {
                "final_decision": "BUY/SELL/HOLD",
                "final_confidence": 85,
                "reasoning": "  ...",
                "layer_results": [...]
            }
        """
        start_time = time.time()

        # [14b × 1] 1개 레이어 심층 분석 (빠른 분석)
        print(f"\n{'='*70}")
        print(f"[v7.4 SINGLE] 1 LLM (14b × 1) 앙상블 시작...")
        print(f"{'='*70}")
        print(f"[DEBUG] 모델: 14b × 1 (빠른 분석)")
        print(f"[DEBUG] 실행: Layer 49-96 (전략 + 리스크)")
        print(f"[DEBUG] 예상 시간: 약 45초")
        print(f"[DEBUG] market_data keys: {list(market_data.keys())}")
        print(f"[DEBUG] trade_history 개수: {len(trade_history)}")
        print(f"[DEBUG] meta_insights 개수: {len(meta_insights)}")

        # 1개 레이어 실행 (전략 + 리스크)
        sequence = [
            "layer_49_96"    # 49-96: 전략 + 리스크
        ]

        results = []
        accumulated_context = ""  # 이전 레이어 결과 축적

        for i, model_key in enumerate(sequence, 1):
            model_info = self.models[model_key]
            layer_range = model_info["layer_emulation"]
            model_name = model_info.get("model", self.base_model)

            print(f"\n[ENSEMBLE {i}/1] Layer {layer_range} | 모델: {model_name} | 역할: {model_info['role']}")
            print(f"[DEBUG] Ollama API 호출 준비...")
            print(f"[DEBUG] _analyze_single_model 호출 시작")

            # 단일 모델 분석
            result = self._analyze_single_model(
                model_key,
                model_info,
                market_data,
                trade_history,
                meta_insights,
                previous_context=accumulated_context
            )

            results.append(result)

            #      (:  )
            accumulated_context += f"L{layer_range}:{result['decision']}({result['confidence']}%) "

            print(f"[ENSEMBLE Layer {layer_range}] : {result['decision']} ({result['confidence']}%)")

        #  (strategist)    
        final_layer = results[-1]

        #    
        votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for r in results:
            votes[r["decision"]] += 1

        #
        layer_summary = "\n".join([
            f"- {r.get('role', 'Unknown Layer')} (Layer {self.models[list(self.models.keys())[i]]['layer_emulation']}): "
            f"{r['decision']} ({r['confidence']}%)"
            for i, r in enumerate(results)
        ])

        final_reasoning = (
            f"===    (32b ) ===\n"
            f"{layer_summary}\n\n"
            f"  :\n"
            f"{final_layer['reasoning']}"
        )

        elapsed = time.time() - start_time

        print(f"[ENSEMBLE]  : {final_layer['decision']} "
              f"({final_layer['confidence']}%) | "
              f" : {votes} | {elapsed:.1f}")

        return {
            "final_decision": final_layer["decision"],
            "final_confidence": final_layer["confidence"],
            "votes": votes,
            "reasoning": final_reasoning,
            "layer_results": results,
            "elapsed_time": round(elapsed, 1)
        }

    def analyze_parallel(self, market_data: Dict, trade_history: List[Dict],
                        meta_insights: List[Dict]) -> Dict:
        """
           sequential  
        """
        return self.analyze_sequential(market_data, trade_history, meta_insights)

    def _analyze_single_model(self, model_key: str, model_info: Dict,
                             market_data: Dict, trade_history: List[Dict],
                             meta_insights: List[Dict], previous_context: str = "") -> Dict:
        """단일 모델 분석 (프롬프트 + LLM 호출)"""

        print(f"[DEBUG] _analyze_single_model 진입 (model_key: {model_key})")

        # 역할별 프롬프트 생성
        print(f"[DEBUG] 프롬프트 생성 시작...")
        prompt = self._create_role_specific_prompt(
            model_key, model_info, market_data, trade_history, meta_insights,
            previous_context
        )
        print(f"[DEBUG] 프롬프트 생성 완료 (길이: {len(prompt)} chars)")

        #   temperature 
        temperature = model_info.get("temperature", 0.3)
        model_to_use = model_info.get("model", self.base_model)  #  

        # LLM 호출
        try:
            # 디버깅: 프롬프트 크기
            prompt_size = len(prompt)
            print(f"[DEBUG] 프롬프트: {prompt_size} chars | 모델: {model_to_use} | Temperature: {temperature}")
            if prompt_size > 5000:
                print(f"[WARNING] 프롬프트 매우 큼! ({prompt_size} chars)")

            from datetime import datetime
            print(f"[DEBUG] ===== 큐잉 디버깅 =====")
            print(f"[DEBUG] 요청 URL: {self.ollama_url}/api/generate")
            print(f"[DEBUG] 모델: {model_to_use}")
            print(f"[DEBUG] 시간: {datetime.now().strftime('%H:%M:%S')}")

            # 포트 확인
            import socket
            port = self.ollama_url.split(':')[-1].split('/')[0]
            print(f"[DEBUG] 포트: {port}")

            # 연결 테스트
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', int(port)))
                sock.close()
                if result == 0:
                    print(f"[DEBUG] 포트 {port} 연결 OK")
                else:
                    print(f"[DEBUG] 포트 {port} 연결 실패!")
            except Exception as e:
                print(f"[DEBUG] 포트 확인 오류: {e}")

            print(f"[DEBUG] Ollama API 호출 시작 ({self.ollama_url})")

            api_start = time.time()
            timeout_sec = 300  # 5분 타임아웃

            # 진행상황 표시 쓰레드 시작
            progress_stop = threading.Event()
            progress_start_time = time.time()

            def show_progress():
                while not progress_stop.is_set():
                    progress_stop.wait(10)  # 10초마다
                    if not progress_stop.is_set():
                        elapsed = int(time.time() - progress_start_time)
                        minutes = elapsed // 60
                        seconds = elapsed % 60
                        if minutes > 0:
                            print(f"  ... 분석 진행 중: {minutes}분 {seconds}초 경과 (예상: 1-3분)")
                        else:
                            print(f"  ... 분석 진행 중: {seconds}초 경과 (예상: 1-3분)")

            progress_thread = threading.Thread(target=show_progress, daemon=True)
            progress_thread.start()

            # Ollama API 형식
            print(f"[DEBUG] ===== HTTP 요청 전송 =====")
            print(f"[DEBUG] POST {self.ollama_url}/api/generate")
            print(f"[DEBUG] Body: model={model_to_use}, temp={temperature}, stream=False")
            print(f"[DEBUG] Timeout: {timeout_sec}초")

            import subprocess
            # Ollama 프로세스 확인
            try:
                result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=3)
                for line in result.stdout.split('\n'):
                    if '11435' in line and 'LISTEN' in line:
                        print(f"[DEBUG] 포트 11435 상태: {line.strip()}")
            except:
                pass

            print(f"[DEBUG] 요청 전송 중... (시작 시간: {datetime.now().strftime('%H:%M:%S.%f')[:-3]})")

            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model_to_use,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": False,
                        "keep_alive": "5m"  # 5분 RAM 해제 (메모리 절약)
                    },
                    timeout=timeout_sec
                )
                print(f"[DEBUG] 응답 수신! (종료 시간: {datetime.now().strftime('%H:%M:%S.%f')[:-3]})")
            except requests.exceptions.Timeout as e:
                print(f"[ERROR] ===== 타임아웃 발생! =====")
                print(f"[ERROR] {timeout_sec}초 타임아웃")
                print(f"[ERROR] 예외: {e}")
                raise
            except Exception as e:
                print(f"[ERROR] ===== HTTP 요청 실패! =====")
                print(f"[ERROR] 예외 타입: {type(e).__name__}")
                print(f"[ERROR] 예외 내용: {e}")
                raise

            api_elapsed = time.time() - api_start

            # 진행상황 표시 쓰레드 중지
            progress_stop.set()
            progress_thread.join(timeout=1)

            print(f"[DEBUG] ===== HTTP 응답 처리 =====")
            print(f"[DEBUG] Status: {response.status_code}")
            print(f"[DEBUG] Headers: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                llm_output = result.get('response', '')

                minutes = int(api_elapsed) // 60
                seconds = int(api_elapsed) % 60
                time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"

                # 큐잉 디버깅: 응답 정보
                print(f"[DEBUG] ===== 응답 완료 =====")
                print(f"[DEBUG] 포트 {port} 응답 완료")
                print(f"[DEBUG] 소요 시간: {time_str}")
                if api_elapsed > 120:  # 2분 이상
                    print(f"[WARNING] 큐잉 의심! 정상: 30-90초, 실제: {time_str}")

                print(f"[완료] 분석 완료! (소요 시간: {time_str}, 응답 길이: {len(llm_output)} chars)")

                # JSON
                parsed = self._parse_llm_response(llm_output)
                parsed["model"] = model_key
                parsed["role"] = model_info["role"]

                return parsed
            else:
                raise Exception(f"HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            progress_stop.set()  # 진행상황 표시 중지
            elapsed = time.time() - api_start
            print(f"[ERROR] Ollama ! (: {elapsed:.0f}, : {prompt_size} chars)")
            return {
                "model": model_key,
                "decision": "HOLD",
                "confidence": 50,
                "reasoning": f"Ollama  ({elapsed:.0f})"
            }
        except Exception as e:
            progress_stop.set()  # 진행상황 표시 중지
            elapsed = time.time() - api_start
            print(f"[ERROR] LLM  : {e} (: {elapsed:.0f})")
            return {
                "model": model_key,
                "decision": "HOLD",
                "confidence": 50,
                "reasoning": f"LLM  : {e}"
            }

    def _create_role_specific_prompt(self, model_key: str, model_info: Dict,
                                    market_data: Dict, trade_history: List[Dict],
                                    meta_insights: List[Dict], previous_context: str = "") -> str:
        """      (   )"""

        role = model_info["role"]
        focus = model_info["focus"]
        timeframe = model_info["timeframe"]
        layer_range = model_info.get("layer_emulation", "unknown")

        #
        current_price = market_data.get('current_price', 0)
        price_history_1m = market_data.get('price_history_1m', [])
        price_history_5m = market_data.get('price_history_5m', [])

        # [NEW] 강화된 추세 분석 메트릭
        recent_peak = market_data.get('recent_peak', current_price)
        decline_from_peak = market_data.get('decline_from_peak_pct', 0)
        short_momentum = market_data.get('short_momentum_pct', 0)
        mid_momentum = market_data.get('mid_momentum_pct', 0)
        momentum_weakening = market_data.get('momentum_weakening', 0)
        pattern_signal = market_data.get('pattern_signal', '횡보')
        current_direction = market_data.get('current_direction', None)

        #     (: )
        context_section = ""
        if previous_context:
            context_section = f" : {previous_context}\n"

        # 8    ( ) -
        timeframe = model_info.get("timeframe", "all")

        #     +   [강화]
        if timeframe == "1m":
            recent_prices = price_history_1m[-5:] if len(price_history_1m) >= 5 else price_history_1m
            change = ((current_price - recent_prices[0]) / recent_prices[0] * 100) if recent_prices else 0
            trend = "" if change > 0.5 else "" if change < -0.5 else ""

            # [NEW] 추세 반전 경고 추가
            reversal_alert = ""
            if decline_from_peak < -1.5:
                reversal_alert = f" 고점대비{abs(decline_from_peak):.1f}%하락"
            if momentum_weakening > 1.0:
                reversal_alert += f" 모멘텀약화{momentum_weakening:.1f}%"

            data_desc = f"1 {trend}({change:+.1f}%) {recent_prices}{reversal_alert}"

        elif timeframe == "5m":
            recent_prices = price_history_5m[-5:] if len(price_history_5m) >= 5 else price_history_5m
            change = ((current_price - recent_prices[0]) / recent_prices[0] * 100) if recent_prices else 0
            trend = "" if change > 1.0 else "" if change < -1.0 else ""

            # [NEW] 추세 반전 경고
            reversal_alert = ""
            if decline_from_peak < -2.0:
                reversal_alert = f" 고점${recent_peak:.1f}→현재하락{abs(decline_from_peak):.1f}%"
            if pattern_signal == "하락_패턴":
                reversal_alert += " 하락패턴감지"

            data_desc = f"5 {trend}({change:+.1f}%) {recent_prices}{reversal_alert}"

        elif timeframe in ["15m", "30m", "1h"]:
            recent_prices = price_history_5m[-8:] if len(price_history_5m) >= 8 else price_history_5m
            change = ((current_price - recent_prices[0]) / recent_prices[0] * 100) if recent_prices else 0
            trend = "" if change > 1.5 else "" if change < -1.5 else ""

            # [NEW] 중기 추세 반전 분석
            reversal_alert = ""
            if current_direction == "BULL" and decline_from_peak < -2.0:
                reversal_alert = f" BULL포지션인데 고점대비 {abs(decline_from_peak):.1f}%하락!"
            if current_direction == "BEAR" and decline_from_peak > -0.5:
                reversal_alert = f" BEAR포지션인데 하락없음 - 반전?"

            data_desc = f" {trend}({change:+.1f}%) {recent_prices}{reversal_alert}"

        else:
            # //  -    +   [강화]
            recent_prices = price_history_1m[-3:] if len(price_history_1m) >= 3 else price_history_1m
            loss_count = len([t for t in trade_history[-10:] if isinstance(t, dict) and t.get('pnl_percent', 0) < 0])
            win_rate = ((10-loss_count)/10*100) if trade_history else 50

            # [NEW] 전략 레이어에 추세 반전 신호 강조
            reversal_info = ""
            if decline_from_peak < -2.0 and current_direction == "BULL":
                reversal_info = f" BULL→BEAR전환고려! 고점${recent_peak:.1f}에서{abs(decline_from_peak):.1f}%하락"
            elif momentum_weakening > 1.5:
                reversal_info = f" 추세약화{momentum_weakening:.1f}% 전환신호"
            elif pattern_signal == "하락_패턴" and current_direction == "BULL":
                reversal_info = f" 하락패턴감지(현재BULL)"
            elif pattern_signal == "상승_패턴" and current_direction == "BEAR":
                reversal_info = f" 상승패턴감지(현재BEAR)"

            data_desc = f"{recent_prices} {win_rate:.0f}%{reversal_info}"

        #    
        recent_10 = trade_history[-10:] if len(trade_history) >= 10 else trade_history
        if recent_10:
            wins = len([t for t in recent_10 if isinstance(t, dict) and t.get('pnl_percent', 0) > 0])
            recent_win_rate = (wins / len(recent_10) * 100) if recent_10 else 0
            last_3_decisions = [t.get('decision', 'HOLD') if isinstance(t, dict) else 'HOLD' for t in trade_history[-3:]]
            stats_info = f"{recent_win_rate:.0f}% 3:{'/'.join(last_3_decisions)}"
        else:
            stats_info = ""

        #    ()
        strategy_hint = ""
        if meta_insights and len(meta_insights) > 0:
            #  3
            top_strategies = meta_insights[-3:]
            strategy_summary = []
            for s in top_strategies:
                if not isinstance(s, dict):
                    continue
                insights = s.get('insights', {})
                win_patterns = insights.get('winning_patterns', [])
                if win_patterns:
                    #
                    pattern = win_patterns[0] if isinstance(win_patterns, list) else str(win_patterns)[:50]
                    strategy_summary.append(pattern[:30])
            if strategy_summary:
                strategy_hint = f"\n:{';'.join(strategy_summary[:2])}"

        # [NEW] 포지션 정보 및 청산 판단 추가
        position = market_data.get('position', 'NONE')
        position_pnl = market_data.get('position_pnl', 0)

        position_info = ""
        if position != 'NONE':
            position_info = f"\n현재포지션: {position} | PNL: {position_pnl:+.2f}%"

        # [NEW] 손실 거래 패턴 경고 (최근 10개 거래에서 손실 패턴 추출)
        loss_patterns = []
        if trade_history:
            recent_losses = [t for t in trade_history[-20:] if isinstance(t, dict) and t.get('pnl_pct', 0) < -0.5]

            for loss in recent_losses[-5:]:  # 최근 5개 손실만
                loss_trend_1m = loss.get('market_1m_trend', '')
                loss_trend_5m = loss.get('market_5m_trend', '')
                loss_side = loss.get('side', '')
                loss_pnl = loss.get('pnl_pct', 0)

                if loss_trend_1m or loss_trend_5m:
                    loss_patterns.append(
                        f"{loss_side}진입({loss_trend_1m}/{loss_trend_5m})→손실{loss_pnl:.1f}%"
                    )

        loss_warning = ""
        if loss_patterns:
            loss_warning = f"\n과거실패:{';'.join(loss_patterns[:3])}"

        # [CORE_PHILOSOPHY] 절대적 임계치 설정 금지 - LLM 자율 학습 기반 판단
        # 주석: 손절선이 아닌 이상 절대적 임계치 설정 금지 및 상황에 대한 학습 필요
        # 주석: 이렇게 llm에게 학습을 시켜야지 절대적 임계치를 설정하면 끝이 없다
        # 이유:
        # - 시장 상황은 동적 (bull/bear/sideways)
        # - 고정 임계치는 특정 상황에서만 유효
        # - LLM이 과거 성공/실패 패턴 학습 → 상황별 자율 판단
        # - 예: 횡보장 -1% vs 급락장 -1% → 의미 완전히 다름
        #
        #   (:  +  + positions + failures + LLM autonomous learning)
        prompt = f"""{role} Layer{layer_range} | {focus}
{context_section}:${current_price} | {data_desc}
{stats_info}{position_info}{loss_warning}{strategy_hint}

규칙 (LLM 자율 판단 - 절대적 임계치 사용 금지):
1. [핵심] 추세선 돌파(trendline breakout) 명확히 인식!
    사용자 피드백: "횡보장 판단보다 추세돌파를 명확히 인식하는게 더 중요"
   - 이유: 횡보/추세 구분보다 추세선 돌파 감지가 실제 수익 핵심
   - 예: 고점 $4558 → 현재 $4421 (-3%) = 상승추세선 하향돌파 → SELL
   - 횡보장 진입 금지는 부차적, 추세돌파 놓치면 수익 기회 상실
2. 포지션 보유 중 청산 판단 (LLM 자율 결정):
    절대 %로 판단 금지! PNL + 시장 맥락 + 과거 학습으로 종합 판단
   - 작은 수익에서 청산? → 추세 강하면 유지, 반등 조짐 있으면 청산
   - 큰 수익에서 청산? → 추세 지속이면 유지, 되돌림 위험 있으면 청산
   - 손실 중 청산? → 추세 전환 신호 + 과거 실패 패턴 유사성 검토
   - 예: PNL +5%지만 강한 하락 추세 지속 → 유지
   - 예: PNL +20%지만 반등 시작 + 과거 이 지점에서 수익 반납 → 청산
3. 과거 실패 패턴 회피: 동일한 시장 상황 반복 금지
4. 손실/이익 판단은 LLM이 시장 맥락 보고 자율 결정 (고정 % 금지)

 선택지 (4가지만 사용 - 명확성 향상):
1. HOLD: 현재 포지션 유지 (또는 관망)
2. CLOSE: 현재 포지션 청산만 (수익/손실 실현, 신규 진입 없음)
3. BUY: 매수 진입 (포지션 있으면 청산 후 진입)
4. SELL: 매도 진입 (포지션 있으면 청산 후 진입)

 예시:
- 현재 SELL +30% → CLOSE 선택 → 수익 실현
- 현재 SELL +30% → BUY 선택 → 청산 후 반대 포지션
- 현재 SELL +30% → HOLD 선택 → 포지션 유지
- 포지션 없음 → BUY 선택 → 매수 진입

JSON 형식:
{{"decision":"HOLD","confidence":60,"reasoning":"하락 추세 지속, 포지션 유지"}}
{{"decision":"CLOSE","confidence":80,"reasoning":"반등 조짐, 수익 실현"}}
{{"decision":"BUY","confidence":75,"reasoning":"상승 추세 전환, 매수 진입"}}
{{"decision":"SELL","confidence":85,"reasoning":"하락 추세 시작, 매도 진입"}}
"""

        return prompt

    def _parse_llm_response(self, llm_output: str) -> Dict:
        """LLM  """
        try:
            # JSON 
            start = llm_output.find('{')
            end = llm_output.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = llm_output[start:end]
                parsed = json.loads(json_str)

                return {
                    "decision": parsed.get("decision", "HOLD"),
                    "confidence": int(parsed.get("confidence", 50)),
                    "reasoning": parsed.get("reasoning", "")
                }
        except:
            pass

        #     
        decision = "HOLD"
        confidence = 50

        if "BUY" in llm_output.upper() or "" in llm_output:
            decision = "BUY"
            confidence = 70
        elif "SELL" in llm_output.upper() or "" in llm_output:
            decision = "SELL"
            confidence = 70

        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": llm_output[:200]
        }

    def _vote_and_aggregate(self, results: List[Dict]) -> Dict:
        """ (Layer 13)   ( Transformer  )"""

        # Layer 13 ( )  
        #  GPT-4, Claude        
        final_layer_result = results[-1]  #   = Layer 13 (89-96)

        final_decision = final_layer_result.get("decision", "HOLD")
        final_confidence = final_layer_result.get("confidence", 50)

        #  100% (  )
        consensus = 100

        #  
        reasoning_parts = []
        for result in results:
            model = result.get("model", "unknown")
            role = result.get("role", "unknown")
            decision = result.get("decision", "HOLD")
            conf = result.get("confidence", 50)
            reasoning = result.get("reasoning", "")[:100]

            reasoning_parts.append(
                f"- {role} ({model}): {decision} ({conf}%) - {reasoning}"
            )

        final_reasoning = (
            f"4   : {votes}\n"
            f": {consensus:.0f}%\n"
            f" : {final_decision} ( {final_confidence}%)\n\n"
            f" :\n" + "\n".join(reasoning_parts)
        )

        return {
            "final_decision": final_decision,
            "final_confidence": final_confidence,
            "votes": votes,
            "consensus": round(consensus, 1),
            "reasoning": final_reasoning,
            "individual_results": results
        }

    def _preload_models(self):
        """       """
        # Ollama 서버 연결 확인
        print(f"[DEBUG] LM Studio URL: {self.ollama_url}")
        try:
            health_check = requests.get("http://localhost:11435/v1/models", timeout=5)
            print(f"[DEBUG] Ollama 서버 응답: {health_check.status_code}")
            if health_check.status_code == 200:
                print(f"[DEBUG] Ollama 버전: {health_check.json()}")
        except Exception as e:
            print(f"[WARNING] Ollama 서버 연결 실패: {e}")
            print(f"[WARNING] Ollama 서버가 실행 중인지 확인하세요!")
            print(f"[WARNING] 실행 방법: C:\\Users\\user\\AppData\\Local\\Programs\\Ollama\\ollama.exe serve")
            return

        # RAM_BOOST 비활성화 (첫 실행 시 너무 오래 걸림)
        print(f"[INFO] RAM_BOOST 건너뜀 (첫 LLM 호출 시 자동 로딩됨)")

        # models_to_preload = [self.power_model]
        # for model in set(models_to_preload):
        #     try:
        #         print(f"[RAM_BOOST] {model}   ...")
        #         response = requests.post(
        #             self.ollama_url,
        #             json={"model": model, "prompt": "", "stream": False, ...},
        #             timeout=30
        #         )
        #         if response.status_code == 200:
        #             print(f"[RAM_BOOST] {model}  ! (RAM )")
        #     except Exception as e:
        #         print(f"[RAM_BOOST] {model}   : {e} ( )")
