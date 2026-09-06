#!/usr/bin/env python3
"""
Dividend Universe Screener (v1.0)
High-Speed Multi-Threaded Dividend Reality Screener across Aristocrats, Kings, & Blue-Chip Payers.

Evaluates 60+ premier dividend companies across all 11 GICS sectors.
Enforces institutional cash flow safety, dividend growth streaks, and Chowder rule hurdles.
"""

import sys
import os
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dividend_reality_auditor import DividendRealityAuditor

# ANSI Styling
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Premier Dividend Universe (60+ Tickers across all 11 Sectors)
DIVIDEND_UNIVERSE = [
    # Consumer Defensive (Staples & Cash Cows)
    "PG", "KO", "PEP", "MO", "CL", "MDLZ", "GIS", "KMB", "STZ", "SYY", "ADM", "HSY",
    # Healthcare (Durable Pharma & Medtech)
    "JNJ", "ABBV", "MRK", "PFE", "BMY", "MDT", "AMGN", "GILD", "BDX", "ZTS",
    # Industrials & Defense
    "CAT", "EMR", "ITW", "GWW", "UPS", "FDX", "DE", "HON", "LMT", "GD", "PH",
    # Financial Services & Asset Managers
    "JPM", "BLK", "TROW", "AFL", "CB", "PRU", "MET", "PNC", "USB", "SCHW", "AXP", "GS",
    # Energy & Pipelines
    "XOM", "CVX", "COP", "EOG", "PSX", "KMI", "WMB",
    # Utilities & Infrastructure
    "NEE", "SO", "DUK", "AEP", "SRE",
    # Real Estate (REITs)
    "O", "PLD", "PSA", "EQIX", "DLR", "SPG",
    # Technology & Telecom
    "MSFT", "AAPL", "TXN", "AVGO", "CSCO", "QCOM", "IBM", "ACN", "CMCSA", "VZ", "T"
]


def audit_worker(ticker: str) -> dict:
    """Worker function for concurrent thread auditing."""
    try:
        auditor = DividendRealityAuditor(ticker)
        return auditor.audit()
    except Exception as e:
        return {
            "symbol": ticker,
            "name": ticker,
            "status": "ERROR",
            "safety_score": 0.0,
            "tier": "CRITERIA_FAILS",
            "passed_gates": False,
            "warnings": [str(e)]
        }


def run_dividend_screen(tickers=None, max_workers=16, min_yield=0.0, aristocrats_only=False):
    """Audits the dividend universe concurrently and ranks candidates."""
    if tickers is None:
        tickers = list(set(DIVIDEND_UNIVERSE))

    print(f"\n{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}              DIVIDEND FORTRESS REALITY SCREENER (INSTITUTIONAL UNIVERSE)                                {RESET}")
    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"Auditing {len(tickers)} dividend-paying companies across {max_workers} worker threads...\n")

    start_time = datetime.now()
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_worker, sym): sym for sym in tickers}
        completed = 0
        for f in as_completed(futures):
            completed += 1
            sym = futures[f]
            try:
                res = f.result()
                if res.get("status") != "DATA_ERROR" and res.get("price", 0) > 0:
                    results.append(res)
            except Exception as e:
                pass
            sys.stdout.write(f"\rAuditing dividend leaders... [{completed}/{len(tickers)}] ({sym:<5})")
            sys.stdout.flush()

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n{GREEN}✔ Audit complete: {len(results)}/{len(tickers)} companies audited in {elapsed:.1f}s.{RESET}\n")

    # Filter by user preferences
    if min_yield > 0.0:
        results = [r for r in results if r.get("dividend_yield_pct", 0) >= min_yield]

    if aristocrats_only:
        results = [r for r in results if r.get("is_aristocrat", False) or r.get("is_king", False)]

    # Tiers classification
    fortress = [r for r in results if r["tier"] == "DIVIDEND_FORTRESS"]
    safe = [r for r in results if r["tier"] == "SAFE_COMPOUNDER"]
    moderate = [r for r in results if r["tier"] == "MODERATE_RISK"]
    traps = [r for r in results if r["tier"] == "YIELD_TRAP"]

    print(f"{BOLD}📊 SCREENING SUMMARY & SAFETY CLASSIFICATIONS:{RESET}")
    print(f"  • {GREEN}DIVIDEND FORTRESS{RESET} (Score >= 85): {len(fortress)} stocks (Near-zero cut risk, pristine cash flow)")
    print(f"  • {CYAN}SAFE COMPOUNDER{RESET}   (Score 70-84): {len(safe)} stocks (Solid coverage, durable dividend hikes)")
    print(f"  • {YELLOW}MODERATE RISK{RESET}     (Score 50-69): {len(moderate)} stocks (Higher payout ratio or cyclical risk)")
    print(f"  • {RED}YIELD TRAPS{RESET}       (Score < 50):  {len(traps)} stocks (FCF deficit, debt-funded yield, or cuts)")
    print()

    # Sort qualifiers by Safety Score descending, then Chowder Number descending
    qualifiers = [r for r in results if r["passed_gates"]]
    qualifiers.sort(key=lambda x: (x["safety_score"], x["chowder_number"]), reverse=True)

    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}                            TOP QUALIFYING DIVIDEND FORTRESS CANDIDATES ({len(qualifiers)} STOCKS)                                 {RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

    header = f"{'Ticker':<7} {'Company':<18} {'Sector':<20} {'Safety':<10} {'Yield':<8} {'Streak':<8} {'5Y CAGR':<9} {'FCF Cov':<9} {'Chowder':<9} {'Tier':<18}"
    print(f"{BOLD}{header}{RESET}")
    print(f"{CYAN}{'-'*len(header)}{RESET}")

    for st in qualifiers:
        t_col = GREEN if st["tier"] == "DIVIDEND_FORTRESS" else CYAN
        fcf_str = f"{st['fcf_payout_ratio']*100:.1f}%" if st["fcf_payout_ratio"] is not None else "N/A"
        badge = " [K]" if st["is_king"] else (" [A]" if st["is_aristocrat"] else "")
        row_str = (
            f"{BOLD}{st['symbol']:<7}{RESET} "
            f"{st['name'][:16]:<18} "
            f"{st['sector'][:18]:<20} "
            f"{t_col}{st['safety_score']:>5.1f}/100{RESET}  "
            f"{st['dividend_yield_pct']:>5.2f}%  "
            f"{st['streak_years']:>3}y{badge:<3} "
            f"{st['cagr_5y_pct']:>+6.2f}%  "
            f"{fcf_str:>8}  "
            f"{st['chowder_number']:>6.2f}%  "
            f"{t_col}{st['tier']}{RESET}"
        )
        print(row_str)

    # Highlight High Yield Fortresses (Yield >= 3.5% & Score >= 75)
    high_yield_fortress = [r for r in qualifiers if r["dividend_yield_pct"] >= 3.5 and r["safety_score"] >= 75.0]
    if high_yield_fortress:
        print(f"\n{BOLD}{GREEN}💰 HIGH-YIELD FORTRESSES (Yield ≥ 3.5% with Pristine Cash Flow Coverage):{RESET}")
        for hy in sorted(high_yield_fortress, key=lambda x: x["dividend_yield_pct"], reverse=True):
            fcf_cov = f"{hy['fcf_payout_ratio']*100:.1f}%" if hy['fcf_payout_ratio'] is not None else "N/A"
            print(f"  • {BOLD}{hy['symbol']:<5}{RESET} ({hy['name'][:18]}): Yield: {GREEN}{hy['dividend_yield_pct']:.2f}%{RESET} | FCF Payout: {fcf_cov} | Streak: {hy['streak_years']}y | Score: {hy['safety_score']}/100 [{hy['sector']}]")

    # Highlight Dividend Growth Superchargers (5Y CAGR >= 8% & Score >= 80)
    growth_superchargers = [r for r in qualifiers if r["cagr_5y_pct"] >= 8.0 and r["safety_score"] >= 80.0]
    if growth_superchargers:
        print(f"\n{BOLD}{CYAN}🚀 DIVIDEND GROWTH SUPERCHARGERS (5-Yr Dividend CAGR ≥ 8.0% + Elite Safety):{RESET}")
        for gs in sorted(growth_superchargers, key=lambda x: x["cagr_5y_pct"], reverse=True):
            print(f"  • {BOLD}{gs['symbol']:<5}{RESET} ({gs['name'][:18]}): 5Y CAGR: {CYAN}{gs['cagr_5y_pct']:+.2f}%{RESET} | Yield: {gs['dividend_yield_pct']:.2f}% | Chowder: {gs['chowder_number']:.2f}% | Score: {gs['safety_score']}/100")

    # Warning on Yield Traps
    if traps:
        print(f"\n{BOLD}{RED}⚠ IDENTIFIED YIELD TRAPS TO AVOID (High Risk of Cut / Negative FCF):{RESET}")
        for yt in sorted(traps, key=lambda x: x["safety_score"])[:5]:
            reasons = ", ".join(yt["warnings"]) if yt["warnings"] else "Deficient cash flow or leverage"
            print(f"  • {RED}{yt['symbol']:<5}{RESET} ({yt['name'][:18]}): Score: {yt['safety_score']}/100 | Yield: {yt['dividend_yield_pct']:.2f}% | Issue: {reasons}")

    return qualifiers, results


def main():
    parser = argparse.ArgumentParser(description="Dividend Fortress Reality Screener")
    parser.add_argument("--workers", type=int, default=16, help="Number of concurrent worker threads")
    parser.add_argument("--min-yield", type=float, default=0.0, help="Minimum dividend yield percentage (e.g. 2.5)")
    parser.add_argument("--aristocrats", action="store_true", help="Filter strictly for Dividend Aristocrats and Kings")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    args = parser.parse_args()

    qualifiers, all_results = run_dividend_screen(
        max_workers=args.workers,
        min_yield=args.min_yield,
        aristocrats_only=args.aristocrats
    )

    if args.json:
        print(json.dumps(qualifiers, indent=2))


if __name__ == "__main__":
    main()
