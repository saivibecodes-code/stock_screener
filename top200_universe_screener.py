#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        TOP 200 S&P 500 & NASDAQ 100 DUAL-GATE REALITY SCANNER               ║
║   200-Stock Multi-Sector Institutional Audit & Optimal Fund Allocation       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Expands the universe to the Top 200 US market champions (~$30B to $3T+ market cap):
  - Captures Mega-Caps + High-ROIC "Hidden Champions" in the 101-200 tier
  - Fast concurrent execution (ThreadPoolExecutor with 16 workers)
  - Dual-Gate Institutional Hurdle: Quality Gate (≥6.0), Valuation Gate (≥5.0), Data (≥60%)
  - Builds an institutional 15-20 stock multi-sector diversified portfolio
  - Syncs directly to paper_trade_agent.py

Usage:
    python3 top200_universe_screener.py
    python3 top200_universe_screener.py --capital 1000 --sync-paper
"""

import sys
import os
import argparse
import concurrent.futures
import json
from datetime import datetime

# Ensure venv if run directly
if __name__ == "__main__":
    venv_py = "/Users/sai/seeking_alpha_scraper/venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)

try:
    from stock_reality_auditor import audit_ticker
except ImportError as e:
    print(f"Error loading dependencies: {e}")
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

# The Top 200 US Market Champions across all 11 GICS sectors
TOP_200_UNIVERSE = [
    # Technology (Mega-Caps, Semis, Software, Automation, Electronic Design)
    "AAPL", "MSFT", "NVDA", "AVGO", "TSM", "ORCL", "CRM", "AMD", "QCOM", "ACN",
    "CSCO", "INTU", "AMAT", "IBM", "NOW", "TXN", "LRCX", "ADI", "PANW", "MU",
    "KLAC", "CRWD", "PLTR", "SNPS", "CDNS", "WDAY", "FTNT", "MCHP", "NXPI", "ON",
    "MPWR", "TEL", "APH", "KEYS", "FICO", "ANSS", "HPQ", "GLW",
    # Communication Services & Digital Media
    "GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "EA",
    "TTWO", "WBD", "LYV",
    # Consumer Discretionary (Retail, Auto, Travel, Dining)
    "AMZN", "TSLA", "HD", "MCD", "NKE", "BKNG", "SBUX", "TJX", "LOW", "CMG",
    "ORLY", "AZO", "ROST", "MAR", "HLT", "DHI", "LEN", "YUM", "GM", "F", "LULU", "TSCO",
    # Consumer Staples (Beverages, Household, Food, Retail)
    "WMT", "COST", "PG", "KO", "PEP", "PM", "MO", "CL", "MDLZ", "KMB",
    "STZ", "GIS", "HSY", "KDP", "MNST", "SYY", "ADM",
    # Financial Services (Banks, Payments, Custody, Exchanges, Insurance)
    "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SPGI", "SCHW",
    "CB", "MMC", "PGR", "ICE", "AXP", "MCO", "MSCI", "C", "PNC", "USB",
    "TFC", "AFL", "MET", "PRU", "TRV", "ALL", "AIG", "COF", "DFS", "BK",
    # Healthcare & Life Sciences (Pharma, MedTech, Diagnostics, Managed Care)
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "AMGN",
    "ISRG", "SYK", "BSX", "VRTX", "REGN", "MDT", "GILD", "CI", "ELV", "ZTS",
    "EW", "BDX", "IDXX", "DXCM", "IQV", "MTD", "A", "HUM", "CNC", "COR", "CAH", "MCK", "BMY",
    # Industrials, Aerospace, Defense & Transportation
    "GE", "CAT", "UNP", "HON", "RTX", "LMT", "BA", "DE", "ETN", "PH", "WM", "ADP",
    "ITW", "EMR", "ROK", "AME", "FAST", "ODFL", "CTAS", "URI", "PCAR", "CMI",
    "CSX", "NSC", "FDX", "TDG", "GD", "NOC",
    # Energy (Oil, Gas, Refining, Infrastructure)
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "OXY", "HES", "KMI", "WMB",
    # Materials, Utilities & Real Estate
    "LIN", "SHW", "ECL", "APD", "FCX", "CTVA", "NEM",
    "NEE", "SO", "DUK", "SRE", "AEP", "D",
    "PLD", "AMT", "EQIX", "PSA", "O", "SPG", "DLR"
]

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_portfolio.json")


def scan_single(ticker):
    """Audits a single ticker with error isolation."""
    try:
        res = audit_ticker(ticker)
        return res
    except Exception:
        return None


def run_top200_scan(max_workers=16):
    print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}   SCANNING TOP 200 S&P 500 & NASDAQ 100 LEADERS ACROSS ALL 11 SECTORS                   {RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{DIM}Running multi-threaded institutional audit on {len(TOP_200_UNIVERSE)} stocks with {max_workers} worker threads...{RESET}\n")

    results = []
    start_time = datetime.now()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {executor.submit(scan_single, sym): sym for sym in TOP_200_UNIVERSE}
        completed = 0
        total = len(TOP_200_UNIVERSE)

        for future in concurrent.futures.as_completed(future_to_ticker):
            sym = future_to_ticker[future]
            completed += 1
            sys.stdout.write(f"\r{DIM}Auditing ticker {completed}/{total} [{sym}]...{RESET}")
            sys.stdout.flush()
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception:
                continue

    sys.stdout.write("\r" + " " * 80 + "\r")
    duration = (datetime.now() - start_time).total_seconds()
    print(f"{GREEN}✔ Audit complete: {len(results)}/{len(TOP_200_UNIVERSE)} stocks successfully audited in {duration:.1f}s.{RESET}\n")
    return results


def categorize_and_report(results):
    """Categorizes results into tiers and displays full breakdown."""
    high_conviction = []
    balanced_pass = []
    expensive_moats = []
    value_traps = []
    fails = []

    for r in results:
        code = r["screening_code"]
        if code == "HIGH_CONVICTION":
            high_conviction.append(r)
        elif code == "BALANCED_PASS":
            balanced_pass.append(r)
        elif code == "EXPENSIVE_QUALITY":
            expensive_moats.append(r)
        elif code == "VALUE_TRAP":
            value_traps.append(r)
        else:
            fails.append(r)

    high_conviction.sort(key=lambda x: x["reality_score"], reverse=True)
    balanced_pass.sort(key=lambda x: x["reality_score"], reverse=True)
    expensive_moats.sort(key=lambda x: x["reality_score"], reverse=True)
    value_traps.sort(key=lambda x: x["reality_score"], reverse=True)

    print(f"{BOLD}{CYAN}📊 TOP 200 SCREENING CLASSIFICATION BREAKDOWN:{RESET}")
    print(f"  • {GREEN}{BOLD}Tier 1: HIGH_CONVICTION:{RESET} {len(high_conviction)} stocks (Pass both gates with elite moats)")
    print(f"  • {GREEN}Tier 2: BALANCED_PASS:{RESET}   {len(balanced_pass)} stocks (Pass both gates, fair price)")
    print(f"  • {YELLOW}Tier 3: EXPENSIVE_MOATS:{RESET} {len(expensive_moats)} stocks (Elite Quality ≥6.0, but Valuation <5.0)")
    print(f"  • {RED}Tier 4: VALUE_TRAPS:{RESET}     {len(value_traps)} stocks (Cheap multiples, but weak fundamentals)")
    print(f"  • {RED}Tier 5: CRITERIA_FAILS:{RESET}  {len(fails)} stocks (Fail both quality and valuation)\n")

    all_qualifiers = high_conviction + balanced_pass
    all_qualifiers.sort(key=lambda x: x["reality_score"], reverse=True)

    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}                   TOP QUALIFYING CANDIDATES PASSING ALL DUAL-SCREEN HURDLE GATES ({len(all_qualifiers)} STOCKS)               {RESET}")
    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

    header = f"{'Ticker':<7} {'Company':<18} {'Sector':<20} {'Score':<8} {'Quality':<8} {'Value':<8} {'Gates':<8} {'EPS Gr':<8} {'PEG':<6} {'ROIC':<7} {'Status':<18}"
    print(f"{BOLD}{header}{RESET}")
    print(f"{CYAN}{'-'*len(header)}{RESET}")

    for r in all_qualifiers[:25]:  # Show top 25 qualifiers
        sc = r["reality_score"]
        sc_col = GREEN if sc >= 7.5 else (YELLOW if sc >= 6.0 else RED)
        peg_str = f"{r['peg_ratio']:.1f}x" if r['peg_valid'] and r['peg_ratio'] is not None else "N/A"
        eps_str = f"{r['eps_growth']:+.1f}%" if r['eps_growth'] is not None else "N/A"
        sig_col = GREEN if r["screening_code"] == "HIGH_CONVICTION" else YELLOW

        print(
            f"{BOLD}{r['symbol']:<7}{RESET} "
            f"{r['name'][:16]:<18} "
            f"{r['sector'][:18]:<20} "
            f"{sc_col}{sc:.2f}/10{RESET}  "
            f"Q:{r['quality_score']:.1f}  "
            f"V:{r['valuation_score']:.1f}  "
            f"{GREEN}P/P/P{RESET}   "
            f"{eps_str:<8} "
            f"{peg_str:<6} "
            f"{r['roic']:<7.1f} "
            f"{sig_col}{r['screening_code']:<18}{RESET}"
        )
    if len(all_qualifiers) > 25:
        print(f"{DIM}... and {len(all_qualifiers) - 25} more qualifying candidates.{RESET}")
    print()

    # Show Notable Hidden Champions from the 101-200 tier
    tier2_gems = [r for r in all_qualifiers if r["symbol"] not in TOP_200_UNIVERSE[:100]]
    if tier2_gems:
        print(f"{BOLD}{CYAN}💎 NOTABLE 'HIDDEN CHAMPIONS' DISCOVERED IN THE 101–200 TIER:{RESET}")
        for gem in tier2_gems[:8]:
            peg_str = f"{gem['peg_ratio']:.1f}x" if gem['peg_valid'] and gem['peg_ratio'] is not None else "N/A"
            print(f"  • {BOLD}{gem['symbol']:<5}{RESET} ({gem['name'][:18]:<18}) Score: {GREEN}{gem['reality_score']:.2f}/10{RESET} | Q:{gem['quality_score']:.1f} | V:{gem['valuation_score']:.1f} | ROIC: {gem['roic']:.1f}% | PEG: {peg_str} [{gem['sector']}]")
        print()

    return all_qualifiers


def construct_optimal_portfolio(qualifiers, capital=1000.0):
    """
    Constructs an institutional 14-18 stock diversified portfolio from all qualifying stocks in Top 200.
    Rules:
      - Max 10% in any single stock (broad diversification across winners)
      - Max 30% in any single sector
      - Slices up to 2-3 top stocks per qualifying sector
      - Minimum 5% cash liquidity buffer
    """
    total_capital = float(capital)
    min_cash_buffer = total_capital * 0.05
    usable_capital = total_capital - min_cash_buffer

    # Group qualifiers by sector
    sector_qualifiers = {}
    for q in qualifiers:
        sec = q["sector"]
        sector_qualifiers.setdefault(sec, []).append(q)

    def get_sector_limit(sec):
        if sec == "Technology": return 0.30
        elif sec == "Financial Services": return 0.22
        elif sec == "Healthcare": return 0.18
        elif sec == "Communication Services": return 0.16
        elif sec == "Industrials": return 0.15
        elif sec == "Energy": return 0.12
        elif sec == "Consumer Cyclical": return 0.12
        elif sec == "Consumer Defensive": return 0.12
        else: return 0.10

    # Pick up to top 2-3 stocks per sector
    selected_stocks = []
    for sec, stocks in sector_qualifiers.items():
        stocks.sort(key=lambda x: x["reality_score"], reverse=True)
        max_in_sec = 3 if sec in ["Technology", "Financial Services", "Healthcare", "Industrials"] else 2
        selected_stocks.extend(stocks[:max_in_sec])

    selected_stocks.sort(key=lambda x: x["reality_score"], reverse=True)

    allocations = {}
    sector_spent = {}

    for stock in selected_stocks:
        sym = stock["symbol"]
        sec = stock["sector"]
        score = stock["reality_score"]
        sec_cap_dlrs = total_capital * get_sector_limit(sec)
        current_sec_dlrs = sector_spent.get(sec, 0.0)

        remaining_sec_room = sec_cap_dlrs - current_sec_dlrs
        if remaining_sec_room < (total_capital * 0.03):
            continue

        if stock["screening_code"] == "HIGH_CONVICTION":
            target_pct = 0.08 if score >= 8.5 else 0.07
        else:
            target_pct = 0.05 if score >= 7.5 else 0.04

        target_dollars = total_capital * target_pct
        allocated_dollars = min(target_dollars, remaining_sec_room, usable_capital, total_capital * 0.09)

        if allocated_dollars >= (total_capital * 0.03) and usable_capital >= allocated_dollars:
            allocations[sym] = {
                "stock": stock,
                "amount": allocated_dollars,
                "weight_pct": (allocated_dollars / total_capital) * 100.0,
                "shares": allocated_dollars / stock["price"]
            }
            usable_capital -= allocated_dollars
            sector_spent[sec] = sector_spent.get(sec, 0.0) + allocated_dollars

    final_cash = total_capital - sum(a["amount"] for a in allocations.values())

    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}             OPTIMAL TOP 200 DIVERSIFIED MULTI-SECTOR PORTFOLIO (${total_capital:,.2f} CAPITAL)                     {RESET}")
    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

    header = f"{'Ticker':<7} {'Company':<18} {'Sector':<20} {'Score':<8} {'Shares':<9} {'Price':<10} {'Amount ($)':<12} {'Weight (%)':<11} {'Status':<16}"
    print(f"{BOLD}{header}{RESET}")
    print(f"{CYAN}{'-'*len(header)}{RESET}")

    for sym, item in sorted(allocations.items(), key=lambda x: x[1]["weight_pct"], reverse=True):
        st = item["stock"]
        sig_col = GREEN if st["screening_code"] == "HIGH_CONVICTION" else YELLOW
        print(
            f"{BOLD}{sym:<7}{RESET} "
            f"{st['name'][:16]:<18} "
            f"{st['sector'][:18]:<20} "
            f"{st['reality_score']:.2f}/10  "
            f"{item['shares']:<9.4f} "
            f"${st['price']:<9.2f} "
            f"${item['amount']:<11.2f} "
            f"{item['weight_pct']:>5.1f}%      "
            f"{sig_col}{st['screening_code']:<16}{RESET}"
        )

    print(f"\n{BOLD}CASH SAFETY BUFFER:{RESET}       ${final_cash:,.2f} ({final_cash/total_capital*100:.1f}% uninvested dry powder)")
    print(f"{BOLD}TOTAL CAPITAL DEPLOYED:{RESET}   ${total_capital - final_cash:,.2f} (across {len(allocations)} positions in {len(sector_spent)} sectors)\n")

    print(f"{BOLD}PORTFOLIO SECTOR EXPOSURE:{RESET}")
    for sec, dlrs in sorted(sector_spent.items(), key=lambda x: x[1], reverse=True):
        pct = (dlrs / total_capital) * 100.0
        print(f"  • {sec:<24} {pct:>5.1f}%  (${dlrs:,.2f})")
    print()

    return allocations, final_cash


def sync_to_paper_agent(allocations, final_cash, total_capital=1000.0):
    """Saves the top-200 diversified portfolio into paper_portfolio.json."""
    now = datetime.now().isoformat()
    positions = {}
    transactions = [{
        "timestamp": now,
        "action": "RESET_TOP200",
        "ticker": "USD",
        "shares": 0.0,
        "price": 1.0,
        "amount": total_capital,
        "cash_after": total_capital,
        "realized_pnl": 0.0,
        "reason": "Top 200 S&P/Nasdaq Multi-Sector Universe Rebalancing"
    }]

    cur_cash = total_capital
    for sym, item in allocations.items():
        st = item["stock"]
        positions[sym] = {
            "shares": item["shares"],
            "cost_basis_per_share": st["price"],
            "total_cost": item["amount"],
            "first_bought_at": now,
            "last_updated": now,
            "last_score": st["reality_score"],
            "screening_code": st["screening_code"]
        }
        cur_cash -= item["amount"]
        transactions.append({
            "timestamp": now,
            "action": "BUY",
            "ticker": sym,
            "shares": item["shares"],
            "price": st["price"],
            "amount": item["amount"],
            "cash_after": cur_cash,
            "realized_pnl": 0.0,
            "reason": f"Top 200 Screen Rank #{len(positions)} (Q:{st['quality_score']:.1f}, V:{st['valuation_score']:.1f})"
        })

    portfolio_data = {
        "version": "3.1-Top200",
        "created_at": now,
        "last_updated": now,
        "initial_cash": total_capital,
        "cash": final_cash,
        "watchlist": list(allocations.keys()),
        "positions": positions,
        "transactions": transactions
    }

    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio_data, f, indent=2)

    print(f"{GREEN}✔ Successfully synced Top-200 Diversified Portfolio to {PORTFOLIO_FILE}!{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="Top 200 S&P 500 & NASDAQ 100 Dual-Gate Screener & Portfolio Allocator")
    parser.add_argument("--workers", type=int, default=16, help="Number of concurrent worker threads (default: 16)")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital to allocate (default: 1000)")
    parser.add_argument("--sync-paper", action="store_true", help="Sync results directly into paper_trade_agent ledger")

    args = parser.parse_args()

    results = run_top200_scan(max_workers=args.workers)
    qualifiers = categorize_and_report(results)

    if qualifiers:
        allocations, final_cash = construct_optimal_portfolio(qualifiers, capital=args.capital)
        if args.sync_paper:
            sync_to_paper_agent(allocations, final_cash, total_capital=args.capital)


if __name__ == "__main__":
    main()
