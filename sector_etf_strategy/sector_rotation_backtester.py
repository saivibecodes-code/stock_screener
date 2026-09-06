#!/usr/bin/env python3
"""
Sector ETF Dual-Momentum Rotation Backtester (v1.0)
Backtests Quantitative Sector Rotation vs Buy-and-Hold S&P 500 (SPY) and Equal-Weight (RSP).

Methodology:
1. Rebalancing: Quarterly or Monthly dual-momentum ranking across all 11 GICS Sectors.
2. Market Safety Filter: SPY vs 200-day Simple Moving Average.
   - Bull Regime (SPY > 200 SMA): 100% allocated to Top 3 leading sectors.
   - Bear Regime (SPY <= 200 SMA): 50% Cash + 50% Defensive Sectors (XLU, XLP, XLV).
3. Zero lookahead bias: Rebalancing decisions strictly use trailing 3M/6M performance.
"""

import sys
import os
import argparse
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BOLD = "\033[1m"
RESET = "\033[0m"

SECTORS = ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLB", "XLRE", "XLC"]


def run_sector_backtest(start_date="2021-01-01", end_date="2026-09-01", initial_capital=1000.0, rebalance_freq="Q"):
    """Runs dual-momentum sector rotation backtest from start_date to end_date."""
    print(f"\n{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}              SECTOR ROTATION HISTORICAL BACKTEST & MACRO REGIME ENGINE                                  {RESET}")
    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"Period: {start_date} to {end_date} | Capital: ${initial_capital:,.2f} | Rebalancing: {rebalance_freq}\n")

    tickers = SECTORS + ["SPY", "RSP"]

    # Fetch extended history to calculate 200-day SMA from day 1
    fetch_start = (pd.to_datetime(start_date) - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    print(f"Downloading historical daily close prices for {len(tickers)} symbols...")
    raw = yf.download(tickers, start=fetch_start, end=end_date, progress=False)
    close_df = raw["Close"].dropna(how="all")

    # SPY 200-day SMA
    spy_close = close_df["SPY"]
    spy_200_sma = spy_close.rolling(200).mean()

    # Align dates from start_date onwards
    active_dates = [d for d in close_df.index if d >= pd.to_datetime(start_date)]
    if not active_dates:
        print(f"{RED}Error: No data available for backtest period.{RESET}")
        return

    # Determine rebalancing schedule
    # Rebalance on first trading day of each Quarter or Month
    rebalance_dates = []
    prev_period = None
    for dt in active_dates:
        cur_period = (dt.year, dt.quarter) if rebalance_freq == "Q" else (dt.year, dt.month)
        if cur_period != prev_period:
            rebalance_dates.append(dt)
            prev_period = cur_period

    print(f"Total trading days: {len(active_dates)} | Total Rebalance Events: {len(rebalance_dates)}")

    # Simulation State
    rot_capital = initial_capital
    rot_shares = {}
    rot_cash = 0.0

    rot_values = []
    spy_values = []
    rsp_values = []
    dates_tracked = []

    # Benchmark tracking
    p0_spy = close_df["SPY"].loc[active_dates[0]]
    spy_shares = initial_capital / p0_spy

    p0_rsp = close_df["RSP"].loc[active_dates[0]]
    rsp_shares = initial_capital / p0_rsp

    rotation_log = []

    # Daily simulation loop
    current_holdings = []
    for dt in active_dates:
        # Check for Rebalance Event
        if dt in rebalance_dates:
            # Liquidate current holdings
            if rot_shares:
                liquidation_val = sum(rot_shares[s] * close_df[s].loc[dt] for s in rot_shares) + rot_cash
                rot_capital = liquidation_val
                rot_shares = {}
                rot_cash = 0.0

            # 1. Check Macro Safety Filter: SPY vs 200-day SMA
            cur_spy = spy_close.loc[dt]
            cur_sma = spy_200_sma.loc[dt]
            is_bull = cur_spy >= cur_sma if not np.isnan(cur_sma) else True

            # 2. Calculate Trailing Momentum for all 11 sectors
            # Trailing 63-day and 126-day returns
            idx_loc = close_df.index.get_loc(dt)
            mom_scores = {}
            for s in SECTORS:
                p_now = close_df[s].loc[dt]
                p_3m = close_df[s].iloc[max(0, idx_loc - 63)]
                p_6m = close_df[s].iloc[max(0, idx_loc - 126)]

                r_3m = (p_now / p_3m) - 1.0 if p_3m > 0 else 0.0
                r_6m = (p_now / p_6m) - 1.0 if p_6m > 0 else 0.0
                mom_scores[s] = (0.6 * r_3m) + (0.4 * r_6m)

            # Sort sectors
            ranked_sectors = sorted(mom_scores.items(), key=lambda x: x[1], reverse=True)

            if is_bull:
                # Bull Market: Top 3 Leading Sectors
                selected_sectors = [s[0] for s in ranked_sectors[:3]]
                alloc_capital = rot_capital
                per_sector = alloc_capital / len(selected_sectors)
                for s in selected_sectors:
                    px = close_df[s].loc[dt]
                    rot_shares[s] = per_sector / px if px > 0 else 0.0
                regime_note = "BULL"
            else:
                # Bear Market: 50% Cash + 50% Defensive Sectors (XLU, XLP, XLV)
                defensive_basket = ["XLU", "XLP", "XLV"]
                rot_cash = rot_capital * 0.50
                per_sector = (rot_capital * 0.50) / len(defensive_basket)
                for s in defensive_basket:
                    px = close_df[s].loc[dt]
                    rot_shares[s] = per_sector / px if px > 0 else 0.0
                selected_sectors = defensive_basket
                regime_note = "BEAR (Defensive/Cash)"

            current_holdings = selected_sectors
            rotation_log.append({
                "date": dt.strftime("%Y-%m-%d"),
                "regime": regime_note,
                "sectors": selected_sectors,
                "capital": rot_capital
            })

        # Calculate daily portfolio equity
        daily_rot_val = sum(rot_shares[s] * close_df[s].loc[dt] for s in rot_shares) + rot_cash
        daily_spy_val = spy_shares * close_df["SPY"].loc[dt]
        daily_rsp_val = rsp_shares * close_df["RSP"].loc[dt]

        dates_tracked.append(dt)
        rot_values.append(daily_rot_val)
        spy_values.append(daily_spy_val)
        rsp_values.append(daily_rsp_val)

    # Compute Performance Statistics
    years = (dates_tracked[-1] - dates_tracked[0]).days / 365.25

    def get_stats(vals):
        end_v = vals[-1]
        tot_ret = ((end_v / initial_capital) - 1.0) * 100.0
        cagr = ((end_v / initial_capital) ** (1.0 / years) - 1.0) * 100.0
        s = pd.Series(vals)
        peak = s.cummax()
        dd = (s - peak) / peak
        max_dd = dd.min() * 100.0

        daily_ret = s.pct_change().dropna()
        sharpe = (daily_ret.mean() / daily_ret.std()) * np.sqrt(252) if daily_ret.std() > 0 else 0.0
        return end_v, tot_ret, cagr, max_dd, sharpe

    rot_end, rot_tot, rot_cagr, rot_dd, rot_sh = get_stats(rot_values)
    spy_end, spy_tot, spy_cagr, spy_dd, spy_sh = get_stats(spy_values)
    rsp_end, rsp_tot, rsp_cagr, rsp_dd, rsp_sh = get_stats(rsp_values)

    print(f"\n{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}                            5-YEAR BACKTEST PERFORMANCE COMPARISON                                       {RESET}")
    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

    header = f"{'Strategy / Benchmark':<32} {'Final Value':<14} {'Total Return':<14} {'CAGR':<9} {'Max DD':<11} {'Sharpe':<8}"
    print(f"{BOLD}{header}{RESET}")
    print(f"{CYAN}{'-'*len(header)}{RESET}")

    def print_row(name, end_val, tot_ret, cagr, max_dd, sharpe, col=WHITE):
        print(f"{BOLD}{col}{name:<32}{RESET} ${end_val:>10,.2f}   {col}{tot_ret:>+10.2f}%{RESET}   {col}{cagr:>5.2f}%{RESET}   {RED}{max_dd:>9.2f}%{RESET}  {col}{sharpe:>6.2f}{RESET}")

    print_row("Tactical Sector Rotation", rot_end, rot_tot, rot_cagr, rot_dd, rot_sh, GREEN)
    print_row("S&P 500 Buy & Hold (SPY)", spy_end, spy_tot, spy_cagr, spy_dd, spy_sh, CYAN)
    print_row("Equal Weight S&P (RSP)", rsp_end, rsp_tot, rsp_cagr, rsp_dd, rsp_sh, WHITE)

    alpha_dollars = rot_end - spy_end
    alpha_pct = rot_tot - spy_tot

    print(f"\n{BOLD}🎯 STRATEGY ALPHA & ROTATION INSIGHTS:{RESET}")
    print(f"  • Net Outperformance vs SPY:   {BOLD}{GREEN}{alpha_pct:+.2f}% (+${alpha_dollars:,.2f}){RESET}")
    print(f"  • Sharpe Ratio:                {GREEN}{rot_sh:.2f}{RESET} (vs SPY: {spy_sh:.2f})")
    print(f"  • Max Drawdown:                {GREEN}{rot_dd:.2f}%{RESET} (vs SPY: {RED}{spy_dd:.2f}%{RESET})")

    print(f"\n{BOLD}📜 KEY HISTORICAL SECTOR ROTATIONS EXECUTED:{RESET}")
    for evt in rotation_log[-8:]:
        sec_str = ", ".join(evt["sectors"])
        print(f"  • {BOLD}{evt['date']}{RESET} [{evt['regime']}]: Allocated to {CYAN}{sec_str}{RESET} (Portfolio: ${evt['capital']:,.2f})")
    print()


def main():
    parser = argparse.ArgumentParser(description="Sector Rotation Backtester")
    parser.add_argument("--start", default="2021-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-09-01", help="End date (YYYY-MM-DD)")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital in USD")
    parser.add_argument("--freq", default="Q", choices=["M", "Q"], help="Rebalance frequency: M (Monthly) or Q (Quarterly)")
    args = parser.parse_args()

    run_sector_backtest(
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        rebalance_freq=args.freq
    )


if __name__ == "__main__":
    main()
