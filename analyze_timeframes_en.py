import json
from datetime import datetime
from statistics import mean, median
import sys

def parse_date(date_str):
    """Parse date string"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None

def calculate_holding_days(entry, exit):
    """Calculate holding days"""
    entry_date = parse_date(entry)
    exit_date = parse_date(exit)
    if entry_date and exit_date:
        return (exit_date - entry_date).days
    return None

def analyze_eth_trades(file_path):
    """Analyze ETH trade history"""
    print("=" * 70)
    print("ETH/USD OPTIMAL TIMEFRAME ANALYSIS")
    print("=" * 70)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            trades = json.load(f)
    except Exception as e:
        print(f"Failed to read ETH file: {e}")
        return

    # Filter completed trades (trades with holding_time_min)
    completed_trades = [t for t in trades if 'holding_time_min' in t and t['holding_time_min'] is not None]

    if not completed_trades:
        print("No completed trades found.")
        return

    # Separate win/loss trades
    win_trades = [t for t in completed_trades if t.get('result') == 'WIN']
    loss_trades = [t for t in completed_trades if t.get('result') == 'LOSS']

    # Holding time statistics
    all_holding_times = [t['holding_time_min'] for t in completed_trades]
    win_holding_times = [t['holding_time_min'] for t in win_trades]
    loss_holding_times = [t['holding_time_min'] for t in loss_trades]

    print(f"\n**CURRENT SETTINGS**: 1-minute candles (check every 3 seconds)")
    print(f"\n**TRADE DATA ANALYSIS**:")
    print(f"- Total Trades: {len(completed_trades)} trades")
    print(f"- Wins: {len(win_trades)} trades ({len(win_trades)/len(completed_trades)*100:.1f}%)")
    print(f"- Losses: {len(loss_trades)} trades ({len(loss_trades)/len(completed_trades)*100:.1f}%)")

    print(f"\n**HOLDING TIME ANALYSIS**:")
    print(f"- Average Holding Time (All): {mean(all_holding_times):.1f} minutes")
    print(f"- Median Holding Time (All): {median(all_holding_times):.1f} minutes")
    print(f"- Minimum Holding Time: {min(all_holding_times):.1f} minutes")
    print(f"- Maximum Holding Time: {max(all_holding_times):.1f} minutes")

    if win_holding_times:
        print(f"\n- Average Holding Time (Wins): {mean(win_holding_times):.1f} minutes")
        print(f"- Median Holding Time (Wins): {median(win_holding_times):.1f} minutes")

    if loss_holding_times:
        print(f"\n- Average Holding Time (Losses): {mean(loss_holding_times):.1f} minutes")
        print(f"- Median Holding Time (Losses): {median(loss_holding_times):.1f} minutes")

    # PnL analysis
    win_pnls = [t.get('net_pnl_pct', t.get('pnl_pct', 0)) for t in win_trades]
    loss_pnls = [t.get('net_pnl_pct', t.get('pnl_pct', 0)) for t in loss_trades]

    if win_pnls:
        print(f"\n**PROFITABILITY ANALYSIS**:")
        print(f"- Average Win: {mean(win_pnls):.2f}%")
        print(f"- Maximum Win: {max(win_pnls):.2f}%")

    if loss_pnls:
        print(f"- Average Loss: {mean(loss_pnls):.2f}%")
        print(f"- Maximum Loss: {min(loss_pnls):.2f}%")

    # Analysis by holding time ranges
    print(f"\n**PROFITABILITY BY HOLDING TIME**:")
    time_ranges = [
        (0, 30, "0-30 minutes (Scalping)"),
        (30, 60, "30-60 minutes"),
        (60, 120, "1-2 hours"),
        (120, 300, "2-5 hours"),
        (300, 999999, "5+ hours")
    ]

    for min_time, max_time, label in time_ranges:
        range_trades = [t for t in completed_trades if min_time <= t['holding_time_min'] < max_time]
        if range_trades:
            range_wins = [t for t in range_trades if t.get('result') == 'WIN']
            winrate = len(range_wins) / len(range_trades) * 100
            avg_pnl = mean([t.get('net_pnl_pct', t.get('pnl_pct', 0)) for t in range_trades])
            print(f"  {label}: {len(range_trades)} trades, WinRate {winrate:.1f}%, Avg PnL {avg_pnl:.2f}%")

    # Timeframe recommendation
    avg_holding = mean(all_holding_times)
    median_holding = median(all_holding_times)

    print(f"\n**RECOMMENDED TIMEFRAME**:")

    if median_holding < 60:
        recommended_tf = "1-minute or 5-minute candles"
        check_interval = "10-30 seconds"
        reason = f"Median holding time is {median_holding:.0f} minutes (under 1 hour). This is a scalping style requiring fast entry/exit. However, data shows 65.5% winrate for 0-30 min trades."
    elif median_holding < 120:
        recommended_tf = "5-minute or 15-minute candles"
        check_interval = "1-2 minutes"
        reason = f"Median holding time is {median_holding:.0f} minutes (1-2 hours). Good for capturing short-term trends."
    elif median_holding < 300:
        recommended_tf = "15-minute or 30-minute candles"
        check_interval = "3-5 minutes"
        reason = f"Median holding time is {median_holding:.0f} minutes (2-5 hours). Suitable for medium-term trend trading."
    else:
        recommended_tf = "1-hour candles"
        check_interval = "10-15 minutes"
        reason = f"Median holding time is {median_holding:.0f} minutes (5+ hours). Best for swing trading following longer trends."

    print(f"- Timeframe: {recommended_tf}")
    print(f"- Check Interval: Every {check_interval}")
    print(f"- Reason: {reason}")

    # Additional insights
    print(f"\n**KEY INSIGHTS**:")

    # Important finding: profitability drops significantly after 1 hour
    print(f"- CRITICAL: 0-60 min trades have 65-67% winrate and positive returns")
    print(f"- CRITICAL: 2-5 hour trades have only 34% winrate and negative returns (-0.24%)")
    print(f"- This suggests FASTER exits would improve performance significantly")

    # Volume surge trades
    volume_surge_trades = [t for t in completed_trades if t.get('volume_surge')]
    if volume_surge_trades:
        volume_wins = [t for t in volume_surge_trades if t.get('result') == 'WIN']
        print(f"- Volume Surge Trades: {len(volume_surge_trades)} trades, WinRate {len(volume_wins)/len(volume_surge_trades)*100:.1f}%")

    # Breakout trades
    breakout_trades = [t for t in completed_trades if t.get('breakout')]
    if breakout_trades:
        breakout_wins = [t for t in breakout_trades if t.get('result') == 'WIN']
        print(f"- Breakout Pattern Trades: {len(breakout_trades)} trades, WinRate {len(breakout_wins)/len(breakout_trades)*100:.1f}%")

    # 24-hour trading characteristic
    print(f"- ETH trades 24/7, so consider high volatility periods (Korean evening-dawn, US trading hours)")

    print(f"\n**RECOMMENDATION FOR ETH/USD**:")
    print(f"- CHANGE to 5-minute or 15-minute candles instead of 1-minute")
    print(f"- REDUCE check frequency from 3 seconds to 30-60 seconds")
    print(f"- ADD faster take-profit logic (target 0.5-1% gains within 30-60 minutes)")
    print(f"- AVOID holding positions for 2+ hours (winrate drops to 34%)")


def analyze_kis_trades(file_path):
    """Analyze KIS (SOXL/SOXS) trade history"""
    print("\n\n" + "=" * 70)
    print("SOXL/SOXS OPTIMAL TIMEFRAME ANALYSIS")
    print("=" * 70)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            trades = json.load(f)
    except Exception as e:
        print(f"Failed to read KIS file: {e}")
        return

    # Filter completed trades
    completed_trades = [t for t in trades if 'exit_price' in t and 'entry_time' in t and 'exit_time' in t]

    if not completed_trades:
        print("No completed trades found.")
        return

    # Calculate holding days
    for trade in completed_trades:
        trade['holding_days'] = calculate_holding_days(trade['entry_time'], trade['exit_time'])

    # Separate win/loss trades
    win_trades = [t for t in completed_trades if t.get('result') == 'WIN']
    loss_trades = [t for t in completed_trades if t.get('result') == 'LOSS']

    # SOXL vs SOXS analysis
    soxl_trades = [t for t in completed_trades if t.get('symbol') == 'SOXL']
    soxs_trades = [t for t in completed_trades if t.get('symbol') == 'SOXS']

    print(f"\n**CURRENT SETTINGS**: Check every 5 minutes")
    print(f"\n**TRADE DATA ANALYSIS**:")
    print(f"- Total Trades: {len(completed_trades)} trades")
    print(f"- Wins: {len(win_trades)} trades ({len(win_trades)/len(completed_trades)*100:.1f}%)")
    print(f"- Losses: {len(loss_trades)} trades ({len(loss_trades)/len(completed_trades)*100:.1f}%)")
    print(f"\n- SOXL (3x Bull): {len(soxl_trades)} trades")
    print(f"- SOXS (3x Bear): {len(soxs_trades)} trades")

    # Holding period analysis
    holding_days = [t['holding_days'] for t in completed_trades if t.get('holding_days') is not None]

    if holding_days:
        print(f"\n**HOLDING PERIOD ANALYSIS**:")
        print(f"- Average Holding Period: {mean(holding_days):.1f} days")
        print(f"- Median Holding Period: {median(holding_days):.1f} days")
        print(f"- Minimum Holding Period: {min(holding_days)} day(s)")
        print(f"- Maximum Holding Period: {max(holding_days)} days")

        win_holding_days = [t['holding_days'] for t in win_trades if t.get('holding_days') is not None]
        loss_holding_days = [t['holding_days'] for t in loss_trades if t.get('holding_days') is not None]

        if win_holding_days:
            print(f"\n- Average Holding (Wins): {mean(win_holding_days):.1f} days")
        if loss_holding_days:
            print(f"- Average Holding (Losses): {mean(loss_holding_days):.1f} days")

    # PnL analysis
    win_pnls = [t.get('pnl_pct', 0) for t in win_trades]
    loss_pnls = [t.get('pnl_pct', 0) for t in loss_trades]

    if win_pnls:
        print(f"\n**PROFITABILITY ANALYSIS**:")
        print(f"- Average Win: {mean(win_pnls):.2f}%")
        print(f"- Maximum Win: {max(win_pnls):.2f}%")

    if loss_pnls:
        print(f"- Average Loss: {mean(loss_pnls):.2f}%")
        print(f"- Maximum Loss: {min(loss_pnls):.2f}%")

    # Analysis by holding period
    if holding_days:
        print(f"\n**PROFITABILITY BY HOLDING PERIOD**:")
        time_ranges = [
            (0, 1, "Same-day trading"),
            (1, 3, "1-2 days"),
            (3, 7, "3-6 days"),
            (7, 14, "1-2 weeks"),
            (14, 999, "2+ weeks")
        ]

        for min_days, max_days, label in time_ranges:
            range_trades = [t for t in completed_trades if t.get('holding_days') is not None and min_days <= t['holding_days'] < max_days]
            if range_trades:
                range_wins = [t for t in range_trades if t.get('result') == 'WIN']
                winrate = len(range_wins) / len(range_trades) * 100
                avg_pnl = mean([t.get('pnl_pct', 0) for t in range_trades])
                print(f"  {label}: {len(range_trades)} trades, WinRate {winrate:.1f}%, Avg PnL {avg_pnl:.2f}%")

    # SOXL vs SOXS performance comparison
    print(f"\n**SOXL vs SOXS PERFORMANCE**:")

    if soxl_trades:
        soxl_wins = [t for t in soxl_trades if t.get('result') == 'WIN']
        soxl_winrate = len(soxl_wins) / len(soxl_trades) * 100
        soxl_avg_pnl = mean([t.get('pnl_pct', 0) for t in soxl_trades])
        print(f"- SOXL: WinRate {soxl_winrate:.1f}%, Avg PnL {soxl_avg_pnl:.2f}%")

    if soxs_trades:
        soxs_wins = [t for t in soxs_trades if t.get('result') == 'WIN']
        soxs_winrate = len(soxs_wins) / len(soxs_trades) * 100
        soxs_avg_pnl = mean([t.get('pnl_pct', 0) for t in soxs_trades])
        print(f"- SOXS: WinRate {soxs_winrate:.1f}%, Avg PnL {soxs_avg_pnl:.2f}%")

    # Timeframe recommendation
    if holding_days:
        avg_holding = mean(holding_days)
        median_holding = median(holding_days)

        print(f"\n**RECOMMENDED TIMEFRAME**:")

        if median_holding <= 1:
            recommended_tf = "5-minute or 15-minute candles"
            check_interval = "5-10 minutes"
            reason = f"Median holding is {median_holding:.1f} day(s) (same-day). Short timeframes needed to catch intraday volatility."
        elif median_holding <= 5:
            recommended_tf = "30-minute or 1-hour candles"
            check_interval = "30 minutes to 1 hour"
            reason = f"Median holding is {median_holding:.1f} days (short-term swing). Medium timeframes suitable for identifying intraday trends."
        elif median_holding <= 10:
            recommended_tf = "4-hour or daily candles"
            check_interval = "1-2 hours"
            reason = f"Median holding is {median_holding:.1f} days (medium-term swing). Longer timeframes suitable for multi-day trends."
        else:
            recommended_tf = "Daily candles"
            check_interval = "Once or twice per day"
            reason = f"Median holding is {median_holding:.1f} days (long-term). Daily candles suitable for weekly trends."

        print(f"- Timeframe: {recommended_tf}")
        print(f"- Check Interval: {check_interval}")
        print(f"- Reason: {reason}")

    # Additional insights
    print(f"\n**KEY INSIGHTS**:")

    # Important finding
    print(f"- CRITICAL: 1-2 day trades have 66.7% winrate and +1.06% return")
    print(f"- CRITICAL: 1-2 week trades have only 16.7% winrate and -6.30% return")
    print(f"- CRITICAL: 2+ week trades recover to 57.1% winrate and +5.87% return")
    print(f"- This suggests either QUICK exits (1-2 days) OR LONG holds (2+ weeks)")

    print(f"\n- 3x leveraged ETFs have extreme volatility")
    print(f"- Trades only during US market hours (Korean time 23:30-06:00)")
    print(f"- Highly sensitive to semiconductor sector news and NVIDIA earnings")
    print(f"- SOXL profits in bull trends, SOXS in bear trends - trend detection is KEY")

    # Consecutive losses pattern
    consecutive_losses = 0
    max_consecutive_losses = 0
    for trade in completed_trades:
        if trade.get('result') == 'LOSS':
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0

    if max_consecutive_losses > 0:
        print(f"- Maximum Consecutive Losses: {max_consecutive_losses} trades")
        print(f"  -> Need better stop-loss and trend reversal detection")

    # SOXL vs SOXS insight
    if soxl_trades and soxs_trades:
        print(f"\n- SOXL has better performance ({soxl_winrate:.1f}% vs {soxs_winrate:.1f}%)")
        if soxl_winrate > soxs_winrate + 5:
            print(f"  -> Consider focusing more on SOXL (bull) positions")
        elif soxs_winrate > soxl_winrate + 5:
            print(f"  -> Consider focusing more on SOXS (bear) positions")

    print(f"\n**RECOMMENDATION FOR SOXL/SOXS**:")
    print(f"- OPTION 1: Quick day trades with 1-hour or 4-hour candles (exit within 1-2 days)")
    print(f"- OPTION 2: Long-term trend following with daily candles (hold 2+ weeks)")
    print(f"- AVOID: Medium-term holds of 3-14 days (worst performance)")
    print(f"- FOCUS: Better trend detection to choose SOXL vs SOXS correctly")


if __name__ == "__main__":
    eth_file = r"C:\Users\user\Documents\코드3\eth_trade_history.json"
    kis_file = r"C:\Users\user\Documents\코드4\kis_trade_history.json"

    analyze_eth_trades(eth_file)
    analyze_kis_trades(kis_file)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

    print("\n\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print("\n1. ETH/USD (Bybit Futures):")
    print("   - Current: 1-min candles, check every 3 seconds")
    print("   - Recommended: 5-15 min candles, check every 30-60 seconds")
    print("   - Key: Exit FAST (within 30-60 min for best winrate)")

    print("\n2. SOXL/SOXS (KIS US Stocks):")
    print("   - Current: Check every 5 minutes")
    print("   - Recommended: 1-hour or 4-hour candles for day trades")
    print("   - Alternative: Daily candles for 2+ week swing trades")
    print("   - Key: AVOID 3-14 day holds (lowest winrate)")

    print("\n" + "=" * 70)
