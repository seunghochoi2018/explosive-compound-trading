#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수정된 모델 테스트
"""

import sys
import time
from nvdl_nvdq_trading_model_fixed import NVDLNVDQTradingModel

def main():
    print("=== 수정된 모델 테스트 시작 ===\n")

    # API 키
    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    # 모델 생성
    print("1. 모델 생성...")
    model = NVDLNVDQTradingModel(FMP_API_KEY)

    # 데이터 로드
    print("\n2. 데이터 로드...")
    model.data_collector.load_data()

    # 최소 패턴 생성 (테스트용)
    print("\n3. 최소 패턴 생성...")
    model._generate_minimal_patterns()

    # 학습 데이터 준비
    print("\n4. 학습 데이터 준비...")
    X, y = model.prepare_training_data()
    if X is not None:
        print(f"   - 샘플 수: {len(X)}")
        print(f"   - 특성 수: {X.shape[1]}")

    # 모델 학습
    print("\n5. 모델 학습...")
    if X is not None and len(X) > 10:
        success = model.train_models(X, y)
        print(f"   - 학습 성공: {success}")
        print(f"   - is_fitted: {model.is_fitted}")

    # 신호 생성 테스트
    print("\n6. 신호 생성 테스트...")
    for i in range(5):
        print(f"\n   테스트 #{i+1}:")

        # NVDL 신호
        nvdl_signal, nvdl_conf = model.predict_signal('NVDL')
        print(f"   - NVDL: {nvdl_signal} (신뢰도: {nvdl_conf:.6f})")

        # NVDQ 신호
        nvdq_signal, nvdq_conf = model.predict_signal('NVDQ')
        print(f"   - NVDQ: {nvdq_signal} (신뢰도: {nvdq_conf:.6f})")

        # 포트폴리오 신호
        action, symbol, conf = model.get_portfolio_signal()
        print(f"   - 포트폴리오: {action} {symbol} (신뢰도: {conf:.6f})")

        time.sleep(0.5)

    # 모델 저장
    print("\n7. 모델 저장...")
    model.save_models()
    model.save_patterns()
    print("   - 저장 완료")

    print("\n=== 테스트 완료 ===")
    print("수정 사항:")
    print(" GradientBoosting, LogisticRegression 학습 문제 해결")
    print(" 신뢰도 계산 로직 개선 (최소 0.1 보장)")
    print(" 모델 자동 재학습 기능 추가")
    print(" 신호 생성 민감도 향상")

if __name__ == "__main__":
    main()