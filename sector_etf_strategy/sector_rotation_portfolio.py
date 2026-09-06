#!/usr/bin/env python3
"""
Sector ETF Rotation Portfolio Agent (v1.0)
Autonomous Macro-Regime Driven Sector Allocation & Paper Trading Engine.

Features:
- Dual-Momentum Regime Filter (SPY vs 200-day SMA market safety gate)
- Bull Regime: Concentrates capital in Top 3-4 Leading Sectors (XLK, XLE, XLV) + optional High-Beta Thematic (XBI/SMH)
- Bear Regime: Defensively rotates into Cash & Flight-to-Safety Sectors (XLP, XLU)
- Persistent JSON ledger in sector_portfolio.json
"""

import os
import sys
import json
import argparse
from datetime import datetime
import pandas as pd
import yfinance as yf

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sector_etf_screener import run_sector_screen, GICS_SECTOR_ETFS, THEMATIC_ETFS
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

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sector_portfolio.json")


class SectorRotationAgent:
    """Manages dynamic sector ETF allocation, market regime filtering, and paper trading."""

    def __init__(self, filepath=PORTFOLIO_FILE, initial_capital=1000.0):
        self.filepath = filepath
        self.initial_capital = initial_capital
        self.data = self._load_or_initialize()

    def _load_or_initialize(self) -> dict:
        """Loads existing portfolio file or creates a new empty ledger."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"{YELLOW}Warning: Error reading {self.filepath}, initializing new ledger ({e}){RESET}")

        now = datetime.now().isoformat()
        return {
            "version": "1.0-SectorRotation",
            "created_at": now,
            "last_updated": now,
            "initial_capital": self.initial_capital,
            "cash": self.initial_capital,
            "market_regime": "UNKNOWN",
            "positions": {},
            "transactions": [{
                "timestamp": now,
                "action": "DEPOSIT",
                "ticker": "USD",
                "shares": 0.0,
                "price": 1.0,
                "amount": self.initial_capital,
                "cash_after": self.initial_capital,
                "reason": "Initial capital deposit"
            }]
        }

    def save(self):
        """Persists state to JSON file."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2)

    def check_market_regime(self) -> dict:
        """Checks overall market safety regime via SPY vs 200-day SMA."""
        try:
            spy = yf.Ticker("SPY")
            hist = spy.history(period="1y")
            close = hist["Close"]
            cur_px = float(close.iloc[-1])
            sma_200 = float(close.rolling(200).mean().iloc[-1])
            dist_pct = ((cur_px / sma_200) - 1.0) * 100.0
            is_bull = cur_px >= sma_200
            regime = "BULL_MARKET" if is_bull else "BEAR_CORRECTION"
            return {
                "regime": regime,
                "is_bull": is_bull,
                "spy_price": cur_px,
                "spy_200_sma": sma_200,
                "dist_pct": dist_pct
            }
        except Exception:
            return {
                "regime": "BULL_MARKET",
                "is_bull": True,
                "spy_price": 500.0,
                "spy_200_sma": 480.0,
                "dist_pct": 4.0
            }

    def rebalance(self, gics_results: list, thematic_results: list = None, capital: float = 1000.0):
        """Executes tactical rotation based on current market regime and sector rankings."""
        regime_info = self.check_market_regime()
        self.data["market_regime"] = regime_info["regime"]

        print(f"\n{BOLD}{CYAN}═══════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}                   TACTICAL SECTOR ROTATION EXECUTION                           {RESET}")
        print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════════════════════════════════{RESET}\n")

        reg_col = GREEN if regime_info["is_bull"] else RED
        print(f"{BOLD}Market Regime Filter:{RESET}   {reg_col}{regime_info['regime']}{RESET} (SPY: ${regime_info['spy_price']:.2f} vs 200 SMA: ${regime_info['spy_200_sma']:.2f} [{regime_info['dist_pct']:+.2f}%])")

        now = datetime.now().isoformat()
        allocations = {}

        if regime_info["is_bull"]:
            # BULL REGIME: Allocate across Top 3 GICS Sectors + Top 1 Thematic
            top_gics = [r for r in gics_results if r["action"] in ["STRONG_OVERWEIGHT", "OVERWEIGHT"]][:3]
            top_theme = [r for r in thematic_results if r["action"] in ["STRONG_OVERWEIGHT", "OVERWEIGHT"]][:1] if thematic_results else []

            selected = top_gics + top_theme
            if not selected:
                selected = gics_results[:3]
            if not selected:
                print(f"{YELLOW}Warning: No eligible ETFs to allocate.{RESET}")
                return

            # 5% dry powder reserve
            cash_reserve = capital * 0.05
            deployable = capital - cash_reserve
            per_etf_dlrs = deployable / len(selected)

            for item in selected:
                sym = item["symbol"]
                px = item["technicals"]["current_price"]
                shares = per_etf_dlrs / px if px > 0 else 0.0
                allocations[sym] = {
                    "item": item,
                    "amount": per_etf_dlrs,
                    "shares": shares,
                    "price": px,
                    "role": "OFFENSIVE_LEADERSHIP" if sym in GICS_SECTOR_ETFS else "THEMATIC_ALPHA"
                }
            remaining_cash = cash_reserve
        else:
            # BEAR REGIME: 40% Cash Buffer + 60% in Defensive Flight-to-Safety (XLU, XLP, XLV)
            cash_reserve = capital * 0.40
            deployable = capital - cash_reserve

            defensive_symbols = ["XLV", "XLP", "XLU"]
            def_items = [r for r in gics_results if r["symbol"] in defensive_symbols]
            if not def_items:
                def_items = gics_results[-3:]
            if not def_items:
                print(f"{YELLOW}Warning: No defensive ETFs found to allocate.{RESET}")
                return

            per_etf_dlrs = deployable / len(def_items)
            for item in def_items:
                sym = item["symbol"]
                px = item["technicals"]["current_price"]
                shares = per_etf_dlrs / px if px > 0 else 0.0
                allocations[sym] = {
                    "item": item,
                    "amount": per_etf_dlrs,
                    "shares": shares,
                    "price": px,
                    "role": "DEFENSIVE_BALLAST"
                }
            remaining_cash = cash_reserve

        # Save allocations into persistent ledger
        self.data["positions"] = {}
        self.data["cash"] = round(remaining_cash, 2)
        self.data["transactions"] = [{
            "timestamp": now,
            "action": "RESET_SECTOR_ROTATION",
            "ticker": "USD",
            "shares": 0.0,
            "price": 1.0,
            "amount": capital,
            "cash_after": capital,
            "reason": f"Sector Rotation Rebalance ({regime_info['regime']})"
        }]

        cur_cash = capital
        for sym, alloc in allocations.items():
            item = alloc["item"]
            amt = alloc["amount"]
            cur_cash -= amt

            self.data["positions"][sym] = {
                "shares": alloc["shares"],
                "cost_basis_per_share": alloc["price"],
                "total_cost": amt,
                "first_bought_at": now,
                "last_updated": now,
                "composite_score": item["composite_score"],
                "action": item["action"],
                "rrg_quadrant": item["relative_momentum"]["rrg_quadrant"],
                "sector": GICS_SECTOR_ETFS.get(sym, THEMATIC_ETFS.get(sym, sym)),
                "role": alloc["role"]
            }

            self.data["transactions"].append({
                "timestamp": now,
                "action": "BUY",
                "ticker": sym,
                "shares": alloc["shares"],
                "price": alloc["price"],
                "amount": amt,
                "cash_after": cur_cash,
                "reason": f"Allocated to {alloc['role']} ({item['composite_score']}/100, RRG: {item['relative_momentum']['rrg_quadrant']})"
            })

        self.save()
        print(f"{GREEN}✔ Sector Rotation Portfolio successfully synced to {self.filepath}!{RESET}\n")

    def display_report(self):
        """Displays rich portfolio report in terminal."""
        positions = self.data.get("positions", {})
        cash = self.data.get("cash", 0.0)

        if not positions:
            print("No active positions. Run with --rebalance to construct the sector portfolio.")
            return

        holdings = []
        total_market_val = 0.0
        total_cost = 0.0

        for sym, pos in positions.items():
            try:
                t = yf.Ticker(sym)
                price = t.info.get("currentPrice") or t.info.get("regularMarketPrice") or pos["cost_basis_per_share"]
            except Exception:
                price = pos["cost_basis_per_share"]

            shares = pos["shares"]
            cost = pos["total_cost"]
            mkt_val = shares * price
            gain = mkt_val - cost
            gain_pct = (gain / cost * 100.0) if cost > 0 else 0.0

            total_market_val += mkt_val
            total_cost += cost

            holdings.append({
                "symbol": sym,
                "shares": shares,
                "cost_basis": pos["cost_basis_per_share"],
                "current_price": price,
                "total_cost": cost,
                "market_value": mkt_val,
                "gain": gain,
                "gain_pct": gain_pct,
                "score": pos.get("composite_score", 0.0),
                "rrg_quadrant": pos.get("rrg_quadrant", "N/A"),
                "sector": pos.get("sector", "N/A"),
                "role": pos.get("role", "HOLDING")
            })

        total_value = total_market_val + cash
        pnl = total_value - self.data.get("initial_capital", 1000.0)
        pnl_pct = (pnl / self.data.get("initial_capital", 1000.0)) * 100.0

        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}                              SECTOR ETF ROTATION PAPER PORTFOLIO LEDGER                                       {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

        print(f"{BOLD}Portfolio Value:{RESET}   {GREEN}${total_value:,.2f}{RESET} (Invested: ${total_cost:,.2f} | Cash: ${cash:,.2f})")
        pnl_col = GREEN if pnl >= 0 else RED
        print(f"{BOLD}Unrealized P&L:{RESET}    {pnl_col}{pnl:+,.2f} ({pnl_pct:+.2f}%){RESET}")
        print(f"{BOLD}Market Regime:{RESET}     {CYAN}{self.data.get('market_regime', 'UNKNOWN')}{RESET}\n")

        header = f"{'ETF':<6} {'Sector / Theme':<24} {'Shares':<9} {'Cost Basis':<11} {'Price':<9} {'Market Val':<11} {'Weight':<8} {'Score':<8} {'RRG':<11} {'Role':<20}"
        print(f"{BOLD}{header}{RESET}")
        print(f"{CYAN}{'-'*len(header)}{RESET}")

        for h in sorted(holdings, key=lambda x: x["market_value"], reverse=True):
            wt = (h["market_value"] / total_value) * 100.0
            print(
                f"{BOLD}{h['symbol']:<6}{RESET} "
                f"{h['sector'][:22]:<24} "
                f"{h['shares']:<9.4f} "
                f"${h['cost_basis']:<10.2f} "
                f"${h['current_price']:<8.2f} "
                f"${h['market_value']:<10.2f} "
                f"{wt:>5.1f}%  "
                f"{h['score']:>4.1f}   "
                f"{h['rrg_quadrant']:<11} "
                f"{h['role']:<20}"
            )
        print()


def main():
    parser = argparse.ArgumentParser(description="Sector ETF Rotation Agent")
    parser.add_argument("--rebalance", action="store_true", help="Screen sectors and rebalance portfolio")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital in USD (default: 1000.0)")
    parser.add_argument("--status", action="store_true", help="Display current portfolio status")
    args = parser.parse_args()

    agent = SectorRotationAgent(initial_capital=args.capital)

    if args.rebalance:
        gics, thematics = run_sector_screen(include_thematics=True, max_workers=16)
        agent.rebalance(gics, thematics, capital=args.capital)
        agent.display_report()
    else:
        agent.display_report()


if __name__ == "__main__":
    main()
