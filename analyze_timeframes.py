import json
from datetime import datetime
from statistics import mean, median
import sys

def parse_date(date_str):
    """날짜 문자열을 파싱"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None

def calculate_holding_days(entry, exit):
    """보유 일수 계산"""
    entry_date = parse_date(entry)
    exit_date = parse_date(exit)
    if entry_date and exit_date:
        return (exit_date - entry_date).days
    return None

def analyze_eth_trades(file_path):
    """ETH 거래 기록 분석"""
    print("=" * 60)
    print("ETH/USD 최적 타임프레임 분석")
    print("=" * 60)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            trades = json.load(f)
    except Exception as e:
        print(f"ETH 파일 읽기 실패: {e}")
        return

    # 완료된 거래만 필터링 (holding_time_min이 있는 거래)
    completed_trades = [t for t in trades if 'holding_time_min' in t and t['holding_time_min'] is not None]

    if not completed_trades:
        print("완료된 거래 기록이 없습니다.")
        return

    # 수익/손실 거래 분리
    win_trades = [t for t in completed_trades if t.get('result') == 'WIN']
    loss_trades = [t for t in completed_trades if t.get('result') == 'LOSS']

    # 보유 시간 통계
    all_holding_times = [t['holding_time_min'] for t in completed_trades]
    win_holding_times = [t['holding_time_min'] for t in win_trades]
    loss_holding_times = [t['holding_time_min'] for t in loss_trades]

    print(f"\n**현재 설정**: 1분봉 (3초마다 체크)")
    print(f"\n**거래 데이터 분석**:")
    print(f"- 총 거래: {len(completed_trades)}건")
    print(f"- 승리: {len(win_trades)}건 ({len(win_trades)/len(completed_trades)*100:.1f}%)")
    print(f"- 손실: {len(loss_trades)}건 ({len(loss_trades)/len(completed_trades)*100:.1f}%)")

    print(f"\n**보유 시간 분석**:")
    print(f"- 전체 평균 보유 시간: {mean(all_holding_times):.1f}분")
    print(f"- 전체 중앙값 보유 시간: {median(all_holding_times):.1f}분")
    print(f"- 최소 보유 시간: {min(all_holding_times):.1f}분")
    print(f"- 최대 보유 시간: {max(all_holding_times):.1f}분")

    if win_holding_times:
        print(f"\n- 수익 거래 평균 보유: {mean(win_holding_times):.1f}분")
        print(f"- 수익 거래 중앙값: {median(win_holding_times):.1f}분")

    if loss_holding_times:
        print(f"\n- 손실 거래 평균 보유: {mean(loss_holding_times):.1f}분")
        print(f"- 손실 거래 중앙값: {median(loss_holding_times):.1f}분")

    # PnL 분석
    win_pnls = [t.get('net_pnl_pct', t.get('pnl_pct', 0)) for t in win_trades]
    loss_pnls = [t.get('net_pnl_pct', t.get('pnl_pct', 0)) for t in loss_trades]

    if win_pnls:
        print(f"\n**수익성 분석**:")
        print(f"- 평균 수익: {mean(win_pnls):.2f}%")
        print(f"- 최대 수익: {max(win_pnls):.2f}%")

    if loss_pnls:
        print(f"- 평균 손실: {mean(loss_pnls):.2f}%")
        print(f"- 최대 손실: {min(loss_pnls):.2f}%")

    # 보유 시간대별 분석
    print(f"\n**보유 시간대별 수익률**:")
    time_ranges = [
        (0, 30, "0-30분 (초단타)"),
        (30, 60, "30-60분"),
        (60, 120, "1-2시간"),
        (120, 300, "2-5시간"),
        (300, 999999, "5시간 이상")
    ]

    for min_time, max_time, label in time_ranges:
        range_trades = [t for t in completed_trades if min_time <= t['holding_time_min'] < max_time]
        if range_trades:
            range_wins = [t for t in range_trades if t.get('result') == 'WIN']
            winrate = len(range_wins) / len(range_trades) * 100
            avg_pnl = mean([t.get('net_pnl_pct', t.get('pnl_pct', 0)) for t in range_trades])
            print(f"  {label}: {len(range_trades)}건, 승률 {winrate:.1f}%, 평균 수익률 {avg_pnl:.2f}%")

    # 타임프레임 추천
    avg_holding = mean(all_holding_times)
    median_holding = median(all_holding_times)

    print(f"\n**권장 타임프레임**:")

    if median_holding < 60:
        recommended_tf = "1분봉"
        check_interval = "10-30초"
        reason = f"중앙값 보유시간이 {median_holding:.0f}분으로 1시간 미만입니다. 빠른 진입/청산이 필요한 초단타 매매 스타일입니다."
    elif median_holding < 120:
        recommended_tf = "5분봉"
        check_interval = "1-2분"
        reason = f"중앙값 보유시간이 {median_holding:.0f}분으로 1-2시간 범위입니다. 단기 추세를 포착하기에 적합합니다."
    elif median_holding < 300:
        recommended_tf = "15분봉"
        check_interval = "3-5분"
        reason = f"중앙값 보유시간이 {median_holding:.0f}분으로 2-5시간 범위입니다. 중기 추세 매매에 적합합니다."
    else:
        recommended_tf = "1시간봉"
        check_interval = "10-15분"
        reason = f"중앙값 보유시간이 {median_holding:.0f}분으로 5시간 이상입니다. 장기 추세를 따르는 스윙 매매 스타일입니다."

    print(f"- 타임프레임: {recommended_tf}")
    print(f"- 체크 주기: {check_interval}마다")
    print(f"- 이유: {reason}")

    # 추가 인사이트
    print(f"\n**추가 인사이트**:")

    # 볼륨 급증 거래 분석
    volume_surge_trades = [t for t in completed_trades if t.get('volume_surge')]
    if volume_surge_trades:
        volume_wins = [t for t in volume_surge_trades if t.get('result') == 'WIN']
        print(f"- 볼륨 급증 거래: {len(volume_surge_trades)}건, 승률 {len(volume_wins)/len(volume_surge_trades)*100:.1f}%")

    # 돌파 거래 분석
    breakout_trades = [t for t in completed_trades if t.get('breakout')]
    if breakout_trades:
        breakout_wins = [t for t in breakout_trades if t.get('result') == 'WIN']
        print(f"- 돌파 패턴 거래: {len(breakout_trades)}건, 승률 {len(breakout_wins)/len(breakout_trades)*100:.1f}%")

    # 24시간 거래 특성
    print(f"- ETH는 24시간 거래되므로 변동성이 높은 시간대(한국 저녁~새벽, 미국 장중)를 고려해야 합니다.")


def analyze_kis_trades(file_path):
    """KIS (SOXL/SOXS) 거래 기록 분석"""
    print("\n\n" + "=" * 60)
    print("SOXL/SOXS 최적 타임프레임 분석")
    print("=" * 60)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            trades = json.load(f)
    except Exception as e:
        print(f"KIS 파일 읽기 실패: {e}")
        return

    # 완료된 거래만 필터링 (exit_price가 있는 거래)
    completed_trades = [t for t in trades if 'exit_price' in t and 'entry_time' in t and 'exit_time' in t]

    if not completed_trades:
        print("완료된 거래 기록이 없습니다.")
        return

    # 보유 일수 계산
    for trade in completed_trades:
        trade['holding_days'] = calculate_holding_days(trade['entry_time'], trade['exit_time'])

    # 수익/손실 거래 분리
    win_trades = [t for t in completed_trades if t.get('result') == 'WIN']
    loss_trades = [t for t in completed_trades if t.get('result') == 'LOSS']

    # SOXL vs SOXS 분석
    soxl_trades = [t for t in completed_trades if t.get('symbol') == 'SOXL']
    soxs_trades = [t for t in completed_trades if t.get('symbol') == 'SOXS']

    print(f"\n**현재 설정**: 5분 체크 주기")
    print(f"\n**거래 데이터 분석**:")
    print(f"- 총 거래: {len(completed_trades)}건")
    print(f"- 승리: {len(win_trades)}건 ({len(win_trades)/len(completed_trades)*100:.1f}%)")
    print(f"- 손실: {len(loss_trades)}건 ({len(loss_trades)/len(completed_trades)*100:.1f}%)")
    print(f"\n- SOXL (3x 레버리지 롱): {len(soxl_trades)}건")
    print(f"- SOXS (3x 레버리지 숏): {len(soxs_trades)}건")

    # 보유 기간 분석
    holding_days = [t['holding_days'] for t in completed_trades if t.get('holding_days') is not None]

    if holding_days:
        print(f"\n**보유 기간 분석**:")
        print(f"- 평균 보유 기간: {mean(holding_days):.1f}일")
        print(f"- 중앙값 보유 기간: {median(holding_days):.1f}일")
        print(f"- 최소 보유 기간: {min(holding_days)}일")
        print(f"- 최대 보유 기간: {max(holding_days)}일")

        win_holding_days = [t['holding_days'] for t in win_trades if t.get('holding_days') is not None]
        loss_holding_days = [t['holding_days'] for t in loss_trades if t.get('holding_days') is not None]

        if win_holding_days:
            print(f"\n- 수익 거래 평균 보유: {mean(win_holding_days):.1f}일")
        if loss_holding_days:
            print(f"- 손실 거래 평균 보유: {mean(loss_holding_days):.1f}일")

    # PnL 분석
    win_pnls = [t.get('pnl_pct', 0) for t in win_trades]
    loss_pnls = [t.get('pnl_pct', 0) for t in loss_trades]

    if win_pnls:
        print(f"\n**수익성 분석**:")
        print(f"- 평균 수익: {mean(win_pnls):.2f}%")
        print(f"- 최대 수익: {max(win_pnls):.2f}%")

    if loss_pnls:
        print(f"- 평균 손실: {mean(loss_pnls):.2f}%")
        print(f"- 최대 손실: {min(loss_pnls):.2f}%")

    # 보유 기간별 분석
    if holding_days:
        print(f"\n**보유 기간별 수익률**:")
        time_ranges = [
            (0, 1, "당일 매매"),
            (1, 3, "1-2일"),
            (3, 7, "3-6일"),
            (7, 14, "1-2주"),
            (14, 999, "2주 이상")
        ]

        for min_days, max_days, label in time_ranges:
            range_trades = [t for t in completed_trades if t.get('holding_days') is not None and min_days <= t['holding_days'] < max_days]
            if range_trades:
                range_wins = [t for t in range_trades if t.get('result') == 'WIN']
                winrate = len(range_wins) / len(range_trades) * 100
                avg_pnl = mean([t.get('pnl_pct', 0) for t in range_trades])
                print(f"  {label}: {len(range_trades)}건, 승률 {winrate:.1f}%, 평균 수익률 {avg_pnl:.2f}%")

    # SOXL vs SOXS 성과 비교
    print(f"\n**SOXL vs SOXS 성과**:")

    if soxl_trades:
        soxl_wins = [t for t in soxl_trades if t.get('result') == 'WIN']
        soxl_winrate = len(soxl_wins) / len(soxl_trades) * 100
        soxl_avg_pnl = mean([t.get('pnl_pct', 0) for t in soxl_trades])
        print(f"- SOXL: 승률 {soxl_winrate:.1f}%, 평균 수익률 {soxl_avg_pnl:.2f}%")

    if soxs_trades:
        soxs_wins = [t for t in soxs_trades if t.get('result') == 'WIN']
        soxs_winrate = len(soxs_wins) / len(soxs_trades) * 100
        soxs_avg_pnl = mean([t.get('pnl_pct', 0) for t in soxs_trades])
        print(f"- SOXS: 승률 {soxs_winrate:.1f}%, 평균 수익률 {soxs_avg_pnl:.2f}%")

    # 타임프레임 추천
    if holding_days:
        avg_holding = mean(holding_days)
        median_holding = median(holding_days)

        print(f"\n**권장 타임프레임**:")

        if median_holding <= 1:
            recommended_tf = "5분봉 또는 15분봉"
            check_interval = "5-10분"
            reason = f"중앙값 보유기간이 {median_holding:.1f}일로 당일 매매입니다. 미국 장중 변동성을 포착하기 위해 짧은 타임프레임이 적합합니다."
        elif median_holding <= 5:
            recommended_tf = "30분봉 또는 1시간봉"
            check_interval = "30분-1시간"
            reason = f"중앙값 보유기간이 {median_holding:.1f}일로 단기 스윙입니다. 일중 추세를 파악하기 위해 중간 타임프레임이 적합합니다."
        elif median_holding <= 10:
            recommended_tf = "4시간봉 또는 일봉"
            check_interval = "1-2시간"
            reason = f"중앙값 보유기간이 {median_holding:.1f}일로 중기 스윙입니다. 며칠간의 추세를 따르기 위해 긴 타임프레임이 적합합니다."
        else:
            recommended_tf = "일봉"
            check_interval = "하루 1-2회"
            reason = f"중앙값 보유기간이 {median_holding:.1f}일로 장기 포지션입니다. 주간 추세를 따르기 위해 일봉이 적합합니다."

        print(f"- 타임프레임: {recommended_tf}")
        print(f"- 체크 주기: {check_interval}마다")
        print(f"- 이유: {reason}")

    # 추가 인사이트
    print(f"\n**추가 인사이트**:")
    print(f"- 3배 레버리지 ETF로 변동성이 매우 큽니다.")
    print(f"- 미국 장중(한국시간 23:30-06:00)에만 거래되므로 타이밍이 중요합니다.")
    print(f"- 반도체 섹터 뉴스와 NVIDIA 실적에 민감합니다.")
    print(f"- SOXL은 상승장, SOXS는 하락장에서 수익을 냅니다. 추세 판단이 핵심입니다.")

    # 연속 손실 패턴 확인
    consecutive_losses = 0
    max_consecutive_losses = 0
    for trade in completed_trades:
        if trade.get('result') == 'LOSS':
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0

    if max_consecutive_losses > 0:
        print(f"- 최대 연속 손실: {max_consecutive_losses}건 (손절 및 추세 전환 감지 개선 필요)")


if __name__ == "__main__":
    eth_file = r"C:\Users\user\Documents\코드3\eth_trade_history.json"
    kis_file = r"C:\Users\user\Documents\코드4\kis_trade_history.json"

    analyze_eth_trades(eth_file)
    analyze_kis_trades(kis_file)

    print("\n" + "=" * 60)
    print("분석 완료")
    print("=" * 60)
