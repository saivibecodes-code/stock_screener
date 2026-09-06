#!/usr/bin/env python3
"""
Dividend Fortress Portfolio & Cash Flow Agent (v1.0)
Autonomous Paper Trading, Projected Annual Dividend Income (PADI),
Yield on Cost (YOC), Monthly Income Calendar & DRIP Compounding Engine.

Maintains persistent portfolio state in dividend_portfolio.json.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dividend_screener import run_dividend_screen
from dividend_reality_auditor import DividendRealityAuditor

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

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dividend_portfolio.json")


class DividendPortfolioAgent:
    """Manages the persistent dividend paper trading portfolio, DRIP, and income forecasts."""

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
            "version": "1.0-DividendFortress",
            "created_at": now,
            "last_updated": now,
            "initial_capital": self.initial_capital,
            "total_deposited": self.initial_capital,
            "cash": self.initial_capital,
            "total_dividends_collected": 0.0,
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
            }],
            "drip_enabled": True
        }

    def save(self):
        """Persists current state to JSON file."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2)

    def construct_fortress_portfolio(self, qualifiers: list, capital: float = 1000.0):
        """Constructs an optimal, multi-sector 10-12 stock dividend fortress portfolio."""
        print(f"\n{BOLD}{BLUE}Building Optimal Dividend Fortress Portfolio for ${capital:,.2f} Capital...{RESET}\n")

        # Guardrail limits
        max_sector_pct = 0.25      # Max 25% in any single sector
        max_position_pct = 0.10    # Max 10% in any single stock ($100 on $1,000)
        min_position_pct = 0.05    # Min 5% per stock ($50 on $1,000)
        cash_buffer_pct = 0.05     # 5% dry powder reserve ($50)

        usable_capital = capital * (1.0 - cash_buffer_pct)

        # Group qualifiers by sector
        by_sector = {}
        for q in qualifiers:
            sec = q["sector"]
            by_sector.setdefault(sec, []).append(q)

        # Select top 2 highest safety score candidates per sector
        candidates = []
        for sec, stocks in by_sector.items():
            stocks.sort(key=lambda x: (x["safety_score"], x["chowder_number"]), reverse=True)
            # Pick top 2 per sector (or 3 for Industrials / Consumer Defensive / Financials)
            limit = 3 if sec in ["Industrials", "Consumer Defensive", "Financial Services"] else 2
            candidates.extend(stocks[:limit])

        # Sort all candidates by safety score and chowder number
        candidates.sort(key=lambda x: (x["safety_score"], x["chowder_number"]), reverse=True)

        allocations = {}
        sector_spent = {}

        for stock in candidates:
            if usable_capital < (capital * min_position_pct):
                break

            sym = stock["symbol"]
            sec = stock["sector"]
            cur_sec_dollars = sector_spent.get(sec, 0.0)
            max_sec_dollars = capital * max_sector_pct
            room_in_sec = max_sec_dollars - cur_sec_dollars

            if room_in_sec < (capital * min_position_pct):
                continue

            # Target position size
            if stock["tier"] == "DIVIDEND_FORTRESS":
                target_dlrs = capital * max_position_pct  # $100
            else:
                target_dlrs = capital * 0.08             # $80

            dlrs = min(target_dlrs, room_in_sec, usable_capital)
            if dlrs >= (capital * min_position_pct):
                allocations[sym] = {
                    "stock": stock,
                    "target_amount": dlrs,
                    "shares": dlrs / stock["price"]
                }
                usable_capital -= dlrs
                sector_spent[sec] = cur_sec_dollars + dlrs

        # Execute allocations into portfolio
        now = datetime.now().isoformat()
        self.data["positions"] = {}
        self.data["cash"] = capital
        self.data["total_dividends_collected"] = 0.0
        self.data["transactions"] = [{
            "timestamp": now,
            "action": "RESET_DIVIDEND_PORTFOLIO",
            "ticker": "USD",
            "shares": 0.0,
            "price": 1.0,
            "amount": capital,
            "cash_after": capital,
            "reason": "Dividend Fortress Strategy Rebalancing"
        }]

        cur_cash = capital
        for sym, item in allocations.items():
            st = item["stock"]
            shares = item["shares"]
            amt = item["target_amount"]
            cur_cash -= amt

            self.data["positions"][sym] = {
                "shares": shares,
                "cost_basis_per_share": st["price"],
                "total_cost": amt,
                "first_bought_at": now,
                "last_updated": now,
                "dividend_rate": st["dividend_rate"],
                "dividend_yield_pct": st["dividend_yield_pct"],
                "safety_score": st["safety_score"],
                "tier": st["tier"],
                "sector": st["sector"],
                "payout_frequency": st["payout_frequency"],
                "streak_years": st["streak_years"],
                "total_dividends_received": 0.0
            }

            self.data["transactions"].append({
                "timestamp": now,
                "action": "BUY",
                "ticker": sym,
                "shares": shares,
                "price": st["price"],
                "amount": amt,
                "cash_after": cur_cash,
                "reason": f"Allocated to {st['tier']} ({st['safety_score']}/100, Yield: {st['dividend_yield_pct']:.2f}%)"
            })

        self.data["cash"] = round(cur_cash, 2)
        self.save()
        print(f"{GREEN}✔ Fortress Portfolio successfully initialized and saved to {self.filepath}!{RESET}")

    def get_portfolio_status(self) -> dict:
        """Fetches live quotes and compiles comprehensive income metrics."""
        positions = self.data.get("positions", {})
        cash = self.data.get("cash", 0.0)

        if not positions:
            return {
                "positions_count": 0,
                "cash": cash,
                "total_value": cash,
                "total_cost": 0.0,
                "unrealized_pnl": 0.0,
                "padi": 0.0,
                "weighted_yield": 0.0,
                "yield_on_cost": 0.0,
                "holdings": []
            }

        holdings = []
        total_market_val = 0.0
        total_cost = 0.0
        total_annual_div_income = 0.0

        for sym, pos in positions.items():
            try:
                t = yf.Ticker(sym)
                price = t.info.get("currentPrice") or t.info.get("regularMarketPrice") or pos["cost_basis_per_share"]
                div_rate = t.info.get("dividendRate") or pos.get("dividend_rate", 0.0)
            except Exception:
                price = pos["cost_basis_per_share"]
                div_rate = pos.get("dividend_rate", 0.0)

            shares = pos["shares"]
            cost = pos["total_cost"]
            mkt_val = shares * price
            annual_divs = shares * div_rate
            gain = mkt_val - cost
            gain_pct = (gain / cost * 100.0) if cost > 0 else 0.0
            cur_yield = (div_rate / price * 100.0) if price > 0 else 0.0
            yoc = (annual_divs / cost * 100.0) if cost > 0 else 0.0

            total_market_val += mkt_val
            total_cost += cost
            total_annual_div_income += annual_divs

            holdings.append({
                "symbol": sym,
                "shares": shares,
                "cost_basis": pos["cost_basis_per_share"],
                "current_price": price,
                "total_cost": cost,
                "market_value": mkt_val,
                "gain": gain,
                "gain_pct": gain_pct,
                "dividend_rate": div_rate,
                "current_yield": cur_yield,
                "yoc": yoc,
                "annual_income": annual_divs,
                "safety_score": pos.get("safety_score", 0.0),
                "tier": pos.get("tier", "N/A"),
                "sector": pos.get("sector", "N/A"),
                "payout_frequency": pos.get("payout_frequency", "Quarterly"),
                "streak_years": pos.get("streak_years", 0)
            })

        total_portfolio_value = total_market_val + cash
        portfolio_pnl = total_portfolio_value - self.data.get("initial_capital", 1000.0)
        pnl_pct = (portfolio_pnl / self.data.get("initial_capital", 1000.0)) * 100.0
        weighted_yield = (total_annual_div_income / total_market_val * 100.0) if total_market_val > 0 else 0.0
        yield_on_cost = (total_annual_div_income / total_cost * 100.0) if total_cost > 0 else 0.0

        return {
            "positions_count": len(holdings),
            "cash": cash,
            "total_market_val": total_market_val,
            "total_value": total_portfolio_value,
            "total_cost": total_cost,
            "total_pnl": portfolio_pnl,
            "pnl_pct": pnl_pct,
            "padi": total_annual_div_income,
            "weighted_yield": weighted_yield,
            "yield_on_cost": yield_on_cost,
            "holdings": holdings
        }

    def simulate_quarter_drip(self):
        """Simulates receiving one quarter of dividends across all holdings and auto-reinvesting via DRIP."""
        print(f"\n{BOLD}{CYAN}═══════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}              EXECUTING QUARTERLY DRIP (DIVIDEND REINVESTMENT)                  {RESET}")
        print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════════════════════════════════{RESET}\n")

        positions = self.data.get("positions", {})
        if not positions:
            print("No positions found to collect dividends.")
            return

        now = datetime.now().isoformat()
        total_payout = 0.0

        for sym, pos in positions.items():
            t = yf.Ticker(sym)
            price = t.info.get("currentPrice") or pos["cost_basis_per_share"]
            annual_rate = pos.get("dividend_rate", 0.0)

            # Frequency adjustment
            freq = pos.get("payout_frequency", "Quarterly")
            if freq == "Monthly":
                payout_per_share = annual_rate / 12.0 * 3.0  # 3 months in quarter
            else:
                payout_per_share = annual_rate / 4.0

            dividend_cash = pos["shares"] * payout_per_share
            total_payout += dividend_cash

            # DRIP: Buy fractional shares with this dividend cash
            drip_shares = dividend_cash / price if price > 0 else 0.0
            pos["shares"] += drip_shares
            pos["total_cost"] += dividend_cash
            pos["total_dividends_received"] = pos.get("total_dividends_received", 0.0) + dividend_cash

            self.data["transactions"].append({
                "timestamp": now,
                "action": "DIVIDEND_DRIP",
                "ticker": sym,
                "shares": drip_shares,
                "price": price,
                "amount": dividend_cash,
                "cash_after": self.data["cash"],
                "reason": f"Quarterly DRIP reinvestment (+{drip_shares:.4f} shares @ ${price:.2f})"
            })

            print(f"  • {BOLD}{sym:<5}{RESET}: Collected ${dividend_cash:>.2f} dividend ──► Reinvested into {GREEN}+{drip_shares:.4f} shares{RESET} @ ${price:.2f}")

        self.data["total_dividends_collected"] = self.data.get("total_dividends_collected", 0.0) + total_payout
        self.save()

        print(f"\n{GREEN}✔ DRIP Complete: ${total_payout:.2f} total dividends automatically compounded!{RESET}\n")

    def display_monthly_calendar(self, holdings: list):
        """Projects expected cash flow across all 12 calendar months."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        calendar = {m: 0.0 for m in months}
        payout_by_stock = {m: [] for m in months}

        for h in holdings:
            sym = h["symbol"]
            freq = h["payout_frequency"]
            annual_inc = h["annual_income"]

            if freq == "Monthly":
                # Pays in all 12 months
                monthly_amt = annual_inc / 12.0
                for m in months:
                    calendar[m] += monthly_amt
                    payout_by_stock[m].append((sym, monthly_amt))
            else:
                # Determine standard quarterly cycle from ticker dividend history
                try:
                    t = yf.Ticker(sym)
                    recent_dates = t.dividends.tail(4).index
                    cycle_months = [d.strftime("%b") for d in recent_dates]
                except Exception:
                    cycle_months = ["Mar", "Jun", "Sep", "Dec"]

                quarterly_amt = annual_inc / max(1, len(cycle_months))
                for m in cycle_months:
                    if m in calendar:
                        calendar[m] += quarterly_amt
                        payout_by_stock[m].append((sym, quarterly_amt))

        print(f"\n{BOLD}{CYAN}═══════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}              PROJECTED 12-MONTH DIVIDEND CASH FLOW CALENDAR                    {RESET}")
        print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════════════════════════════════{RESET}\n")

        header = f"{'Month':<7} {'Income ($)':<12} {'Payers':<50}"
        print(f"{BOLD}{header}{RESET}")
        print(f"{CYAN}{'-'*75}{RESET}")

        total_projected = 0.0
        for m in months:
            inc = calendar[m]
            total_projected += inc
            payers = ", ".join([f"{s} (${a:.2f})" for s, a in payout_by_stock[m]])
            print(f"{BOLD}{m:<7}{RESET} {GREEN}${inc:>7.2f}{RESET}     {payers}")

        print(f"{CYAN}{'-'*75}{RESET}")
        print(f"{BOLD}TOTAL PROJECTED 12-MONTH CASH FLOW: {GREEN}${total_projected:,.2f}{RESET}\n")

    def display_report(self):
        """Renders comprehensive portfolio report in terminal."""
        st = self.get_portfolio_status()

        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}                             DIVIDEND FORTRESS PAPER PORTFOLIO LEDGER                                          {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

        print(f"{BOLD}Portfolio Value:{RESET}   {GREEN}${st['total_value']:,.2f}{RESET} (Invested: ${st['total_cost']:,.2f} | Cash: ${st['cash']:,.2f})")
        pnl_col = GREEN if st['total_pnl'] >= 0 else RED
        print(f"{BOLD}Total P&L:{RESET}         {pnl_col}{st['total_pnl']:+,.2f} ({st['pnl_pct']:+.2f}%){RESET}")
        print(f"{BOLD}Annual Dividend Inc (PADI):{RESET} {GREEN}${st['padi']:,.2f} / year{RESET}")
        print(f"{BOLD}Weighted Dividend Yield:{RESET}   {CYAN}{st['weighted_yield']:.2f}%{RESET}")
        print(f"{BOLD}Yield on Cost (YOC):{RESET}       {BOLD}{MAGENTA}{st['yield_on_cost']:.2f}%{RESET}")
        print(f"{BOLD}Total Dividends Reinvested:{RESET} ${self.data.get('total_dividends_collected', 0.0):.2f}\n")

        if not st["holdings"]:
            print("No active holdings. Run with --rebalance to construct the fortress portfolio.")
            return

        header = f"{'Ticker':<7} {'Shares':<9} {'Cost Basis':<11} {'Price':<9} {'Market Val':<11} {'Yield':<8} {'YOC':<8} {'Annual Div':<11} {'Safety':<10} {'Sector':<18}"
        print(f"{BOLD}{header}{RESET}")
        print(f"{CYAN}{'-'*len(header)}{RESET}")

        for h in sorted(st["holdings"], key=lambda x: x["annual_income"], reverse=True):
            t_col = GREEN if h["tier"] == "DIVIDEND_FORTRESS" else CYAN
            print(
                f"{BOLD}{h['symbol']:<7}{RESET} "
                f"{h['shares']:<9.4f} "
                f"${h['cost_basis']:<10.2f} "
                f"${h['current_price']:<8.2f} "
                f"${h['market_value']:<10.2f} "
                f"{h['current_yield']:>5.2f}%  "
                f"{h['yoc']:>5.2f}%  "
                f"{GREEN}${h['annual_income']:>6.2f}/yr{RESET}  "
                f"{t_col}{h['safety_score']:>4.1f}/100{RESET}  "
                f"{h['sector'][:16]:<18}"
            )

        self.display_monthly_calendar(st["holdings"])


def main():
    parser = argparse.ArgumentParser(description="Dividend Fortress Portfolio Agent")
    parser.add_argument("--rebalance", action="store_true", help="Screen universe and construct optimal portfolio")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital in USD (default: 1000.0)")
    parser.add_argument("--drip", action="store_true", help="Simulate one quarter of dividend distributions with DRIP")
    parser.add_argument("--status", action="store_true", help="Display current portfolio status and income calendar")
    args = parser.parse_args()

    agent = DividendPortfolioAgent(initial_capital=args.capital)

    if args.rebalance:
        qualifiers, _ = run_dividend_screen(max_workers=16)
        agent.construct_fortress_portfolio(qualifiers, capital=args.capital)
        agent.display_report()
    elif args.drip:
        agent.simulate_quarter_drip()
        agent.display_report()
    else:
        agent.display_report()


if __name__ == "__main__":
    main()
