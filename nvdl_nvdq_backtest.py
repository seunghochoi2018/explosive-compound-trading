#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 백테스트 시뮬레이션
"""

import sys
import time
from datetime import datetime
from nvdl_nvdq_smart_trader import NVDLNVDQSmartTrader

def run_backtest():
    """NVDL/NVDQ 백테스트 실행"""
    print('🧪 NVDL/NVDQ 백테스트 시뮬레이션')
    print('=' * 50)

    trader = NVDLNVDQSmartTrader()

    # 초기 상태 저장
    initial_balance = trader.balance

    print(f'📊 초기 설정:')
    print(f'   시작 잔고: ${initial_balance:,.2f}')
    print(f'   최소 신뢰도: {trader.min_confidence:.1%}')
    print(f'   거래 대상: {", ".join(trader.symbols)}')

    # 여러 번 일일 체크를 실행하여 거래 패턴 확인
    for day in range(1, 11):  # 10일간 시뮬레이션
        print(f'\n📅 Day {day} 거래 시뮬레이션')
        print('-' * 40)

        # 일일 체크 실행
        trader.run_daily_check()

        # 진행 상황 간단 요약
        if trader.total_trades > 0:
            current_win_rate = trader.winning_trades / trader.total_trades * 100
            print(f'   📈 중간 결과: 거래 {trader.total_trades}회, 승률 {current_win_rate:.1f}%')

        # 시간 경과 시뮬레이션
        time.sleep(0.5)

    # 최종 백테스트 결과
    print('\n' + '='*60)
    print('📊 백테스트 최종 결과')
    print('='*60)

    final_return = (trader.balance - initial_balance) / initial_balance * 100

    print(f'💰 초기 잔고: ${initial_balance:,.2f}')
    print(f'💰 최종 잔고: ${trader.balance:,.2f}')
    print(f'📈 총 수익률: {final_return:+.2f}%')
    print(f'🎯 총 거래: {trader.total_trades}회')

    if trader.total_trades > 0:
        win_rate = trader.winning_trades / trader.total_trades * 100
        print(f'🏆 승률: {win_rate:.1f}% ({trader.winning_trades}/{trader.total_trades})')
        print(f'📊 평균 거래당 수익: {trader.total_profit/trader.total_trades:.2f}%')
    else:
        print('⚠️ 거래가 발생하지 않음')

    # 현재 포지션 상태
    if trader.current_positions:
        print(f'\n📍 현재 보유 포지션:')
        for symbol, pos in trader.current_positions.items():
            current_price = trader.get_current_price(symbol)
            if pos['side'] == 'LONG':
                pnl = (current_price - pos['entry_price']) / pos['entry_price'] * 100
            else:
                pnl = (pos['entry_price'] - current_price) / pos['entry_price'] * 100

            print(f'   {symbol} {pos["side"]}: ${pos["entry_price"]:.2f} → ${current_price:.2f} ({pnl:+.1f}%)')
    else:
        print(f'\n📍 현재 포지션: 없음')

    # 학습 상태
    if trader.learning_patterns:
        profitable_patterns = sum(1 for p in trader.learning_patterns.values() if p['wins'] > p['total'] * 0.6)
        print(f'\n🧠 학습 현황: {len(trader.learning_patterns)}개 패턴 학습 (수익패턴: {profitable_patterns}개)')

    print('='*60)

    return {
        'total_trades': trader.total_trades,
        'win_rate': trader.winning_trades / max(1, trader.total_trades) * 100,
        'total_return': final_return,
        'final_balance': trader.balance,
        'learning_patterns': len(trader.learning_patterns)
    }

if __name__ == "__main__":
    try:
        results = run_backtest()
        print(f'\n✅ 백테스트 완료!')
        print(f'   수익률: {results["total_return"]:+.2f}%')
        print(f'   승률: {results["win_rate"]:.1f}%')
        print(f'   거래수: {results["total_trades"]}회')

    except Exception as e:
        print(f'❌ 백테스트 오류: {e}')
        import traceback
        traceback.print_exc()