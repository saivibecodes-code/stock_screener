#!/usr/bin/env python3
"""
Sector ETF Reality Screener (v1.0)
High-Speed Multi-Threaded Sector & Thematic ETF Scanner.

Scans:
- All 11 Official GICS Sector SPDRs (XLK, XLF, XLV, XLY, XLP, XLE, XLI, XLU, XLB, XLRE, XLC)
- Key High-Volume Sub-Industry & Thematic ETFs (SMH, XBI, CIBR, KRE, ITA, XHB, GDX, XOP)

Generates:
- Comprehensive Sector Leadership Heatmap
- Relative Rotation Graph (RRG) Quadrant Map
- Macro Business Cycle Regime Diagnosis (Early, Mid, Late, Contraction)
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
from sector_etf_analyzer import SectorETFAnalyzer

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

# The 11 Official GICS Sector SPDRs
GICS_SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financial Services",
    "XLV": "Healthcare",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication Services"
}

# Key Sub-Industry & Thematic ETFs
THEMATIC_ETFS = {
    "SMH": "Semiconductors",
    "XBI": "Biotechnology",
    "CIBR": "Cybersecurity",
    "KRE": "Regional Banking",
    "ITA": "Aerospace & Defense",
    "XHB": "Homebuilders",
    "GDX": "Gold Miners",
    "XOP": "Oil & Gas Exploration"
}


def audit_worker(ticker: str) -> dict:
    """Worker thread auditing single ETF."""
    try:
        analyzer = SectorETFAnalyzer(ticker)
        return analyzer.analyze()
    except Exception as e:
        return {
            "symbol": ticker,
            "name": ticker,
            "status": "ERROR",
            "composite_score": 0.0,
            "action": "AVOID",
            "warnings": [str(e)]
        }


def diagnose_macro_cycle(gics_results: list) -> dict:
    """Diagnoses macro business cycle regime based on sector leadership."""
    # Top 3 leading sectors
    top_symbols = [r["symbol"] for r in gics_results[:3]]

    early_cycle_sectors = {"XLF", "XLY", "XLI", "XLRE"}
    mid_cycle_sectors = {"XLK", "XLC", "XLI"}
    late_cycle_sectors = {"XLE", "XLB", "XLV"}
    defensive_sectors = {"XLP", "XLU", "XLV"}

    early_score = sum(1 for s in top_symbols if s in early_cycle_sectors)
    mid_score = sum(1 for s in top_symbols if s in mid_cycle_sectors)
    late_score = sum(1 for s in top_symbols if s in late_cycle_sectors)
    def_score = sum(1 for s in top_symbols if s in defensive_sectors)

    scores = {
        "Early-Cycle (Economic Recovery / Expansion)": early_score,
        "Mid-Cycle (Peak Growth / Tech Leadership)": mid_score,
        "Late-Cycle (Inflation / Commodity Outperformance)": late_score,
        "Defensive / Contraction (Staples / Utilities Flight to Safety)": def_score
    }
    predominant_cycle = max(scores, key=scores.get)

    return {
        "cycle": predominant_cycle,
        "top_sectors": top_symbols,
        "scores": scores
    }


def run_sector_screen(include_thematics=True, max_workers=16):
    """Executes high-speed scan across all sector and thematic ETFs."""
    tickers = list(GICS_SECTOR_ETFS.keys())
    if include_thematics:
        tickers += list(THEMATIC_ETFS.keys())

    print(f"\n{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}                   SECTOR ETF ROTATION & RELATIVE MOMENTUM SCREENER                                      {RESET}")
    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"Scanning {len(tickers)} Sector & Thematic ETFs with {max_workers} worker threads...\n")

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
                if res.get("status") != "DATA_ERROR" and "technicals" in res:
                    results.append(res)
            except Exception:
                pass
            sys.stdout.write(f"\rAuditing sector leaders... [{completed}/{len(tickers)}] ({sym:<5})")
            sys.stdout.flush()

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n{GREEN}✔ Scan complete: {len(results)}/{len(tickers)} ETFs analyzed in {elapsed:.1f}s.{RESET}\n")

    # Separate GICS from Thematics
    gics_results = [r for r in results if r["symbol"] in GICS_SECTOR_ETFS]
    thematic_results = [r for r in results if r["symbol"] in THEMATIC_ETFS]

    gics_results.sort(key=lambda x: x["composite_score"], reverse=True)
    thematic_results.sort(key=lambda x: x["composite_score"], reverse=True)

    # 1. 11 GICS SECTORS RANKING
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}                             OFFICIAL 11 GICS SECTOR ROTATION RANKINGS                                         {RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

    header = f"{'Rank':<5} {'ETF':<6} {'Sector Name':<24} {'Score':<9} {'Action':<18} {'RRG State':<12} {'1M Spread':<11} {'3M Spread':<11} {'Trend Regime':<16}"
    print(f"{BOLD}{header}{RESET}")
    print(f"{CYAN}{'-'*len(header)}{RESET}")

    action_colors = {
        "STRONG_OVERWEIGHT": GREEN,
        "OVERWEIGHT": CYAN,
        "NEUTRAL": YELLOW,
        "UNDERWEIGHT": MAGENTA,
        "AVOID": RED
    }

    for idx, r in enumerate(gics_results, 1):
        sym = r["symbol"]
        sec_name = GICS_SECTOR_ETFS.get(sym, sym)
        score = r["composite_score"]
        act = r["action"]
        act_col = action_colors.get(act, WHITE)
        rm = r["relative_momentum"]
        t = r["technicals"]

        rrg_col = GREEN if rm["rrg_quadrant"] == "LEADING" else (CYAN if rm["rrg_quadrant"] == "IMPROVING" else (YELLOW if rm["rrg_quadrant"] == "WEAKENING" else RED))
        t_col = GREEN if "BULLISH" in t["regime"] else RED

        def fmt_sp(val):
            c = GREEN if val >= 0 else RED
            return f"{c}{val:>+6.1f}%{RESET}"

        row_str = (
            f"{idx:<5} "
            f"{BOLD}{sym:<6}{RESET} "
            f"{sec_name:<24} "
            f"{act_col}{score:>5.1f}/100{RESET} "
            f"{act_col}{act:<18}{RESET} "
            f"{rrg_col}{rm['rrg_quadrant']:<12}{RESET} "
            f"{fmt_sp(rm['spread_1m']):<11} "
            f"{fmt_sp(rm['spread_3m']):<11} "
            f"{t_col}{t['regime'][:15]:<16}"
        )
        print(row_str)

    # 2. SUB-INDUSTRY & THEMATIC RANKINGS
    if thematic_results:
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}                         HIGH-BETA & THEMATIC SUB-INDUSTRY SCAN                                            {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

        print(f"{BOLD}{header}{RESET}")
        print(f"{CYAN}{'-'*len(header)}{RESET}")

        for idx, r in enumerate(thematic_results, 1):
            sym = r["symbol"]
            theme_name = THEMATIC_ETFS.get(sym, sym)
            score = r["composite_score"]
            act = r["action"]
            act_col = action_colors.get(act, WHITE)
            rm = r["relative_momentum"]
            t = r["technicals"]
            rrg_col = GREEN if rm["rrg_quadrant"] == "LEADING" else (CYAN if rm["rrg_quadrant"] == "IMPROVING" else (YELLOW if rm["rrg_quadrant"] == "WEAKENING" else RED))
            t_col = GREEN if "BULLISH" in t["regime"] else RED

            row_str = (
                f"{idx:<5} "
                f"{BOLD}{sym:<6}{RESET} "
                f"{theme_name:<24} "
                f"{act_col}{score:>5.1f}/100{RESET} "
                f"{act_col}{act:<18}{RESET} "
                f"{rrg_col}{rm['rrg_quadrant']:<12}{RESET} "
                f"{fmt_sp(rm['spread_1m']):<11} "
                f"{fmt_sp(rm['spread_3m']):<11} "
                f"{t_col}{t['regime'][:15]:<16}"
            )
            print(row_str)

    # 3. MACRO BUSINESS CYCLE DIAGNOSIS
    macro = diagnose_macro_cycle(gics_results)
    print(f"\n{BOLD}{CYAN}🌐 MACRO BUSINESS CYCLE DIAGNOSIS:{RESET}")
    print(f"  • Current Inferred Regime: {BOLD}{GREEN}{macro['cycle']}{RESET}")
    print(f"  • Sector Leadership Basket: {', '.join(macro['top_sectors'])}")
    print(f"  • Tactical Action: Favor {BOLD}{', '.join([GICS_SECTOR_ETFS.get(s, s) for s in macro['top_sectors']])}{RESET} for offensive alpha, rotate out of bottom lagging sectors.\n")

    return gics_results, thematic_results


def main():
    parser = argparse.ArgumentParser(description="Sector ETF Screener")
    parser.add_argument("--workers", type=int, default=16, help="Worker threads")
    parser.add_argument("--no-thematics", action="store_true", help="Scan only the 11 GICS sectors")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    gics, thematics = run_sector_screen(
        include_thematics=not args.no_thematics,
        max_workers=args.workers
    )

    if args.json:
        print(json.dumps({"gics": gics, "thematics": thematics}, indent=2))


if __name__ == "__main__":
    main()
