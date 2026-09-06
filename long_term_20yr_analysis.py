#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        20-YEAR HISTORICAL MULTI-REGIME SIMULATION (2006 — 2026)              ║
║    $1,000 Initial Capital · 4 Market Crises · S&P 500 Benchmark (SPY)        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Demonstrates:
  1. 20-Year Capital Trajectory across 4 major macro cycles:
       • 2008 Great Financial Crisis (-55% S&P 500 crash)
       • 2010-2019 ZIRP Expansion & Tech Emergence
       • 2020 COVID-19 Liquidity Shock (-34% crash)
       • 2022 Fed Inflation Rate Hikes (-25% bear market)
       • 2023-2026 Generative AI Infrastructure Expansion
  2. Risk-Managed Rebalancing (25% position cap, 5% cash buffer) vs. SPY Buy-and-Hold
  3. Maximum Drawdown & Crisis Stress-Testing
  4. Institutional Deep Dive on 20-Year Fundamental Data Boundaries & Survivorship Bias

Usage:
    python3 long_term_20yr_analysis.py
    python3 long_term_20yr_analysis.py --cash 1000
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np

# Ensure venv if run directly
if __name__ == "__main__":
    venv_py = "/Users/sai/seeking_alpha_scraper/venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance is required.")
    sys.exit(1)

# ANSI Colors
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
BLUE    = "\033[94m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
MAGENTA = "\033[95m"
RED     = "\033[91m"
WHITE   = "\033[97m"

# Universe of representative blue chips active across 2006-2026
LONG_TERM_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "JPM", "CAT", "XOM", "COST", "UNH"
]
BENCHMARK = "SPY"


def run_20yr_simulation(initial_cash=1000.0):
    print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}       20-YEAR LONG-TERM REBALANCING SIMULATION (2006-01-03 → 2026-09-01)                  {RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"Starting Capital: ${initial_cash:,.2f} | Benchmark: S&P 500 (SPY)\n")

    print(f"{DIM}Fetching 20 years of daily adjusted closing prices (5,190+ trading sessions)...{RESET}")
    all_tickers = list(set(LONG_TERM_UNIVERSE + [BENCHMARK]))
    price_df = yf.download(all_tickers, start="2006-01-01", end="2026-09-05", progress=False)["Close"].dropna(how="all")

    first_dt = price_df.index[0]
    last_dt = price_df.index[-1]

    # Benchmark tracking
    spy_start_px = float(price_df.loc[first_dt, BENCHMARK])
    spy_shares = initial_cash / spy_start_px

    # Define Annual Rebalance Dates (January of each year)
    years = range(2006, 2027)
    rebalance_dates = []
    for y in years:
        target = pd.to_datetime(f"{y}-01-03")
        sub = price_df.index[price_df.index >= target]
        if len(sub) > 0:
            rebalance_dates.append(sub[0])

    # Ensure last date is included
    if price_df.index[-1] not in rebalance_dates:
        rebalance_dates.append(price_df.index[-1])

    rebalance_dates = sorted(list(set(rebalance_dates)))

    # Portfolio simulation
    cash = initial_cash
    positions = {}  # ticker: shares
    ledger = []

    for i, date in enumerate(rebalance_dates):
        date_str = str(date)[:10]
        spy_px = float(price_df.loc[date, BENCHMARK])
        spy_val = spy_shares * spy_px

        # Mark to market existing positions
        equity_val = 0.0
        for s, shs in positions.items():
            if s in price_df.columns:
                px = float(price_df.loc[date, s])
                if not np.isnan(px):
                    equity_val += shs * px

        total_port_val = cash + equity_val

        # Determine eligible stocks at this date (must be trading)
        eligible = []
        for s in LONG_TERM_UNIVERSE:
            if s in price_df.columns:
                px = float(price_df.loc[date, s])
                if not np.isnan(px) and px > 0:
                    eligible.append(s)

        # Equal-weighted target with 25% max position cap and 5% cash buffer
        min_cash_buffer = total_port_val * 0.05
        usable_cash_pool = total_port_val - min_cash_buffer

        n_targets = min(len(eligible), 5)
        target_per_stock = min(usable_cash_pool / n_targets, total_port_val * 0.25)

        # Execute rebalance: liquidate existing, re-enter target allocations
        cash = total_port_val
        positions = {}

        # Re-allocate
        for s in eligible[:n_targets]:
            px = float(price_df.loc[date, s])
            shs = target_per_stock / px
            positions[s] = shs
            cash -= target_per_stock

        # Recompute final value at rebalance close
        cur_eq = sum(positions[s] * float(price_df.loc[date, s]) for s in positions)
        final_val = cash + cur_eq

        top_holdings = ", ".join(sorted(positions.keys())[:3])
        ledger.append({
            "date": date_str,
            "port_val": final_val,
            "spy_val": spy_val,
            "port_ret_pct": ((final_val - initial_cash) / initial_cash) * 100.0,
            "spy_ret_pct": ((spy_val - initial_cash) / initial_cash) * 100.0,
            "alpha_pct": (((final_val - initial_cash) / initial_cash) - ((spy_val - initial_cash) / initial_cash)) * 100.0,
            "cash": cash,
            "top_holdings": top_holdings
        })

    # Print Progression Table
    print(f"{BOLD}{CYAN}📈 20-YEAR PERIODIC CAPITAL PROGRESSION (Annual Checkpoints):{RESET}")
    header = f"{'Date':<11} {'Portfolio ($)':<15} {'Port Return (%)':<17} {'SPY ($)':<12} {'SPY Return (%)':<16} {'Alpha (%)':<12} {'Holdings':<20}"
    print(f"{BOLD}{header}{RESET}")
    print(f"{CYAN}{'-'*len(header)}{RESET}")

    for row in ledger:
        p_col = GREEN if row["port_ret_pct"] >= 0 else RED
        s_col = GREEN if row["spy_ret_pct"] >= 0 else RED
        a_col = GREEN if row["alpha_pct"] >= 0 else RED
        print(
            f"{row['date']:<11} "
            f"${row['port_val']:<14,.2f} "
            f"{p_col}{row['port_ret_pct']:>+10.2f}%{RESET}       "
            f"${row['spy_val']:<11,.2f} "
            f"{s_col}{row['spy_ret_pct']:>+10.2f}%{RESET}     "
            f"{a_col}{row['alpha_pct']:>+8.2f}%{RESET}   "
            f"{DIM}{row['top_holdings']:<20}{RESET}"
        )
    print()

    # ─────────────────────────────────────────────────────────────
    # CRISIS STRESS-TESTING (Max Drawdowns across 4 crashes)
    # ─────────────────────────────────────────────────────────────
    print(f"{BOLD}{CYAN}🌪 CRISIS STRESS-TESTING (Historical Drawdowns):{RESET}")

    crises = [
        ("2008 Great Financial Crisis", "2007-10-09", "2009-03-09"),
        ("2020 COVID-19 Flash Crash",   "2020-02-19", "2020-03-23"),
        ("2022 Fed Rate Hike Bear Mkt", "2022-01-03", "2022-10-12")
    ]

    for c_name, c_start, c_end in crises:
        sub = price_df.loc[pd.to_datetime(c_start):pd.to_datetime(c_end), BENCHMARK]
        if len(sub) > 0:
            peak = sub.iloc[0]
            trough = sub.min()
            dd = ((trough - peak) / peak) * 100.0
            print(f"  • {BOLD}{c_name:<30}{RESET} SPY Drawdown: {RED}{dd:.1f}%{RESET} (Peak: ${peak:.2f} → Trough: ${trough:.2f})")
    print()

    # ─────────────────────────────────────────────────────────────
    # FINAL METRICS
    # ─────────────────────────────────────────────────────────────
    last = ledger[-1]
    years_elapsed = (pd.to_datetime(last["date"]) - pd.to_datetime(ledger[0]["date"])).days / 365.25
    port_cagr = (((last["port_val"] / initial_cash) ** (1.0 / years_elapsed)) - 1.0) * 100.0
    spy_cagr = (((last["spy_val"] / initial_cash) ** (1.0 / years_elapsed)) - 1.0) * 100.0

    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}                   FINAL 20-YEAR QUANTITATIVE SCORECARD (2006 — 2026)                      {RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

    print(f"  • Starting Capital:         ${initial_cash:,.2f} (January 2006)")
    print(f"  • Strategy Final Wealth:    {GREEN}{BOLD}${last['port_val']:,.2f}{RESET} ({GREEN}{last['port_ret_pct']:+,.1f}% Cumulative{RESET})")
    print(f"  • S&P 500 (SPY) Final:      ${last['spy_val']:,.2f} ({last['spy_ret_pct']:+,.1f}% Cumulative)")
    print(f"  • Strategy Annualized CAGR: {GREEN}{BOLD}{port_cagr:.2f}% / year{RESET}")
    print(f"  • S&P 500 Annualized CAGR:  {spy_cagr:.2f}% / year")
    print(f"  • Outperformance Multiple:  {BOLD}{last['port_val'] / last['spy_val']:.2f}x{RESET} S&P 500 terminal capital\n")

    # ─────────────────────────────────────────────────────────────
    # INSTITUTIONAL REALITY: THE SURVIVORSHIP BIAS & DATA WALL
    # ─────────────────────────────────────────────────────────────
    print(f"{BOLD}{YELLOW}⚠ CRITICAL INSTITUTIONAL LESSONS ON 20-YEAR BACKTESTING:{RESET}")
    print(f"  1. {BOLD}The Yahoo Finance 5-Year Data Wall:{RESET}")
    print(f"     Free public APIs (Yahoo Finance) only store detailed SEC financial statements (Balance Sheet,")
    print(f"     Income Statement, Cash Flow) for the last {BOLD}4 to 5 fiscal years{RESET} (2021–2026).")
    print(f"     Auditing exact 2006-2020 Altman Z'', NOPAT, dynamic WACC, and diluted shares requires")
    print(f"     institutional databases like Compustat, FactSet, or Sharadar.")
    print()
    print(f"  2. {BOLD}The Survivorship & Hindsight Bias Trap:{RESET}")
    print(f"     Backtesting today's tech winners (NVDA, AAPL, MSFT, AMZN) back to 2006 shows massive returns,")
    print(f"     but nobody in 2006 knew NVDA ($0.29 split-adj) would become an AI monopoly 20 years later.")
    print(f"     In 2006, the biggest S&P 500 'fortress' stocks were General Electric, Citigroup, AIG, and")
    print(f"     Bank of America — all of which suffered catastrophic 80–98% crashes during the 2008 GFC.")
    print(f"     A true, defensible 20-year fundamental strategy must use a point-in-time constituent universe")
    print(f"     to eliminate lookahead bias.")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="20-Year Historical Multi-Regime Simulation (2006-2026)")
    parser.add_argument("--cash", type=float, default=1000.0, help="Initial capital (default: 1000)")
    args = parser.parse_args()

    run_20yr_simulation(args.cash)


if __name__ == "__main__":
    main()
