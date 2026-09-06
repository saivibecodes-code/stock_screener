#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             AUTONOMOUS FACT-BASED PAPER TRADING AGENT                        ║
║     Dual-Gate Quality/Valuation Allocation Engine · $1,000 Portfolio         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Built on top of stock_reality_auditor (v3.1):
  - Starting Capital: $1,000.00 cash
  - Fractional share execution with persistent JSON portfolio ledger
  - Strict Rule-Based Entry / Exit:
      • ENTRY: Requires passing all 3 Hurdle Gates (Quality ≥ 6.0, Valuation ≥ 5.0, Data ≥ 60%)
      • SIZING: Max 25% per single position, max 40% per sector, min 5% cash buffer
      • EXIT: Liquidates immediately if Quality fails or stock becomes a Value Trap
      • TRIM: Trims positions drifting into Expensive Quality (>15% weight) or position drift (>28%)

Usage:
    python3 paper_trade_agent.py            # View portfolio dashboard
    python3 paper_trade_agent.py --run      # Run screening cycle & execute paper trades
    python3 paper_trade_agent.py --dry-run  # Preview trades without modifying portfolio
    python3 paper_trade_agent.py --history  # View transaction audit ledger
    python3 paper_trade_agent.py --reset    # Reset portfolio to $1,000.00 cash
    python3 paper_trade_agent.py --add SYM  # Add stock to universe watchlist
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Ensure yfinance and stock_reality_auditor are available
if __name__ == "__main__":
    venv_py = "/Users/sai/seeking_alpha_scraper/venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)

try:
    import yfinance as yf
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

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_portfolio.json")

DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "META", "GOOGL",
    "AMZN", "JPM", "V", "CAT", "UNH", "XOM", "COST", "TSLA",
    "TSM", "LLY"
]


class PaperPortfolioManager:
    """Manages paper trading ledger, portfolio state, and rule-based trade execution."""

    def __init__(self, filepath=PORTFOLIO_FILE):
        self.filepath = filepath
        self.data = self.load_portfolio()

    def load_portfolio(self):
        """Loads existing portfolio state or initializes a new $1,000 portfolio."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"{YELLOW}Warning: Corrupt portfolio file ({e}). Initializing clean state.{RESET}")

        now = datetime.now().isoformat()
        initial_state = {
            "version": "3.1",
            "created_at": now,
            "last_updated": now,
            "initial_cash": 1000.00,
            "cash": 1000.00,
            "watchlist": DEFAULT_WATCHLIST,
            "positions": {},
            "transactions": []
        }
        self.save_portfolio(initial_state)
        return initial_state

    def save_portfolio(self, state=None):
        """Saves portfolio state atomically."""
        if state is None:
            state = self.data
        state["last_updated"] = datetime.now().isoformat()
        with open(self.filepath, "w") as f:
            json.dump(state, f, indent=2)

    def reset_portfolio(self, initial_cash=1000.00):
        """Resets the portfolio back to pristine starting cash."""
        now = datetime.now().isoformat()
        self.data = {
            "version": "3.1",
            "created_at": now,
            "last_updated": now,
            "initial_cash": float(initial_cash),
            "cash": float(initial_cash),
            "watchlist": DEFAULT_WATCHLIST,
            "positions": {},
            "transactions": [{
                "timestamp": now,
                "action": "RESET",
                "ticker": "USD",
                "shares": 0.0,
                "price": 1.0,
                "amount": float(initial_cash),
                "cash_after": float(initial_cash),
                "realized_pnl": 0.0,
                "reason": "Portfolio initialized / reset to baseline cash"
            }]
        }
        self.save_portfolio()
        print(f"{GREEN}✔ Portfolio successfully reset to ${initial_cash:,.2f} cash.{RESET}")

    def add_to_watchlist(self, ticker):
        sym = ticker.upper().strip()
        if sym not in self.data["watchlist"]:
            self.data["watchlist"].append(sym)
            self.save_portfolio()
            print(f"{GREEN}✔ Added {sym} to watchlist.{RESET}")
        else:
            print(f"{YELLOW}{sym} is already in the watchlist.{RESET}")

    def remove_from_watchlist(self, ticker):
        sym = ticker.upper().strip()
        if sym in self.data["watchlist"]:
            self.data["watchlist"].remove(sym)
            self.save_portfolio()
            print(f"{GREEN}✔ Removed {sym} from watchlist.{RESET}")
        else:
            print(f"{YELLOW}{sym} is not in the watchlist.{RESET}")

    def get_portfolio_valuation(self):
        """Computes current market value, unrealized PnL, and weights of all held assets."""
        cash = self.data["cash"]
        positions = self.data["positions"]
        held_tickers = list(positions.keys())

        if not held_tickers:
            return {
                "cash": cash,
                "cash_weight_pct": 100.0,
                "equity_value": 0.0,
                "total_value": cash,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                "positions_detail": {},
                "sector_weights": {}
            }

        # Fetch live prices for held positions
        positions_detail = {}
        equity_val = 0.0
        total_cost = 0.0
        sector_totals = {}

        for sym, pos in positions.items():
            shares = pos["shares"]
            cost_per_share = pos["cost_basis_per_share"]
            cost_basis = pos.get("total_cost", shares * cost_per_share)

            try:
                t = yf.Ticker(sym)
                price = t.info.get("currentPrice") or t.info.get("regularMarketPrice") or pos["cost_basis_per_share"]
                sector = t.info.get("sector") or "Diversified"
            except Exception:
                price = pos["cost_basis_per_share"]
                sector = "Diversified"

            mkt_val = shares * price
            pnl = mkt_val - cost_basis
            pnl_pct = (pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

            equity_val += mkt_val
            total_cost += cost_basis
            sector_totals[sector] = sector_totals.get(sector, 0.0) + mkt_val

            positions_detail[sym] = {
                "shares": shares,
                "cost_basis_per_share": cost_per_share,
                "current_price": price,
                "cost_basis": cost_basis,
                "market_value": mkt_val,
                "unrealized_pnl": pnl,
                "unrealized_pnl_pct": pnl_pct,
                "sector": sector,
                "screening_code": pos.get("screening_code", "UNKNOWN"),
                "last_score": pos.get("last_score", 0.0)
            }

        total_val = cash + equity_val
        total_pnl = total_val - self.data["initial_cash"]
        total_pnl_pct = (total_pnl / self.data["initial_cash"]) * 100.0

        # Calculate weights
        for sym, d in positions_detail.items():
            d["weight_pct"] = (d["market_value"] / total_val * 100.0) if total_val > 0 else 0.0

        sector_weights = {sec: (val / total_val * 100.0) for sec, val in sector_totals.items()}

        return {
            "cash": cash,
            "cash_weight_pct": (cash / total_val * 100.0) if total_val > 0 else 100.0,
            "equity_value": equity_val,
            "total_value": total_val,
            "total_cost": total_cost,
            "unrealized_pnl": total_pnl,
            "unrealized_pnl_pct": total_pnl_pct,
            "positions_detail": positions_detail,
            "sector_weights": sector_weights
        }

    def print_dashboard(self):
        """Renders an institutional paper trading portfolio dashboard."""
        val = self.get_portfolio_valuation()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}             FACT-BASED PAPER TRADING AGENT — PORTFOLIO DASHBOARD                          {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{DIM}As of: {now_str} | Inception: {self.data['created_at'][:19].replace('T', ' ')}{RESET}\n")

        pnl_col = GREEN if val["unrealized_pnl"] >= 0 else RED
        print(f"{BOLD}PORTFOLIO CAPITAL SUMMARY:{RESET}")
        print(f"  • Starting Capital:     ${self.data['initial_cash']:,.2f}")
        print(f"  • Current Net Asset:    {BOLD}${val['total_value']:,.2f}{RESET}")
        print(f"  • Available Cash:       ${val['cash']:,.2f} ({val['cash_weight_pct']:.1f}% allocation)")
        print(f"  • Invested Equity:      ${val['equity_value']:,.2f} ({100 - val['cash_weight_pct']:.1f}% allocation)")
        print(f"  • Total Return:         {pnl_col}{BOLD}{val['unrealized_pnl']:+,.2f} ({val['unrealized_pnl_pct']:+.2f}%){RESET}\n")

        # Held Positions Table
        positions = val["positions_detail"]
        if positions:
            print(f"{BOLD}{CYAN}📊 CURRENT HOLDINGS ({len(positions)} positions):{RESET}")
            header = f"{'Ticker':<7} {'Shares':<9} {'Avg Cost':<10} {'Price':<10} {'Mkt Val':<10} {'Weight':<8} {'Return ($)':<12} {'Return (%)':<11} {'Signal':<16}"
            print(f"{BOLD}{header}{RESET}")
            print(f"{CYAN}{'-'*len(header)}{RESET}")

            for sym, pos in sorted(positions.items(), key=lambda x: x[1]["market_value"], reverse=True):
                r_col = GREEN if pos["unrealized_pnl"] >= 0 else RED
                sig_col = GREEN if pos["screening_code"] in ["HIGH_CONVICTION", "BALANCED_PASS"] else (YELLOW if pos["screening_code"] == "EXPENSIVE_QUALITY" else RED)
                pnl_str = f"${pos['unrealized_pnl']:+,.2f}"
                pnl_pct_str = f"{pos['unrealized_pnl_pct']:+.2f}%"
                print(
                    f"{BOLD}{sym:<7}{RESET} "
                    f"{pos['shares']:<9.4f} "
                    f"${pos['cost_basis_per_share']:<9.2f} "
                    f"${pos['current_price']:<9.2f} "
                    f"${pos['market_value']:<9.2f} "
                    f"{pos['weight_pct']:>5.1f}%  "
                    f"{r_col}{pnl_str:<12}{RESET} "
                    f"{r_col}{pnl_pct_str:<11}{RESET} "
                    f"{sig_col}{pos['screening_code']:<16}{RESET}"
                )
            print()

            # Sector Diversification
            print(f"{BOLD}SECTOR EXPOSURE:{RESET}")
            for sec, w in val["sector_weights"].items():
                w_col = GREEN if w <= 40.0 else RED
                print(f"  • {sec:<24} {w_col}{w:.1f}%{RESET} {'(Exceeds 40% cap)' if w > 40.0 else ''}")
            print()
        else:
            print(f"{YELLOW}No active stock holdings. Portfolio is 100% in cash (${val['cash']:,.2f}).{RESET}")
            print(f"{DIM}Run `python3 paper_trade_agent.py --run` to audit universe and execute entry trades.{RESET}\n")

        # Watchlist
        print(f"{DIM}Watchlist Universe ({len(self.data['watchlist'])} stocks): {', '.join(self.data['watchlist'])}{RESET}\n")

    def print_history(self, limit=20):
        """Displays historical transaction ledger."""
        txs = self.data.get("transactions", [])
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}                   PAPER TRADE TRANSACTION AUDIT LEDGER                                    {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

        if not txs:
            print(f"{YELLOW}No transactions recorded yet.{RESET}\n")
            return

        header = f"{'Date/Time':<19} {'Action':<7} {'Ticker':<7} {'Shares':<9} {'Price':<10} {'Amount':<10} {'Cash After':<11} {'Reason':<30}"
        print(f"{BOLD}{header}{RESET}")
        print(f"{CYAN}{'-'*len(header)}{RESET}")

        for tx in txs[-limit:]:
            act = tx["action"]
            act_col = GREEN if act == "BUY" else (RED if act in ["SELL", "TRIM"] else YELLOW)
            time_str = tx["timestamp"][:19].replace("T", " ")
            print(
                f"{time_str:<19} "
                f"{act_col}{act:<7}{RESET} "
                f"{BOLD}{tx['ticker']:<7}{RESET} "
                f"{tx['shares']:<9.4f} "
                f"${tx['price']:<9.2f} "
                f"${tx['amount']:<9.2f} "
                f"${tx['cash_after']:<10.2f} "
                f"{DIM}{tx.get('reason', '')[:35]}{RESET}"
            )
        print()

    def run_cycle(self, dry_run=False):
        """
        Main autonomous rebalancing and trade execution engine.
        Rule set:
          1. Audit all held positions first.
             - LIQUIDATE if Quality fails (< 5.5) or becomes VALUE_TRAP / FAIL_BOTH.
             - TRIM if position weight > 28% or EXPENSIVE_QUALITY > 15% weight.
          2. Audit watchlist candidates.
             - Filter candidates passing Quality (≥6.0), Valuation (≥5.0), and Data (≥60%).
             - Allocate cash up to targets:
                 HIGH_CONVICTION: Target 20-25%
                 BALANCED_PASS: Target 12-16%
             - Observe sector limit (max 40%) and cash buffer (min 5%).
        """
        mode_str = f"{YELLOW}[DRY RUN PREVIEW — NO CHANGES SAVED]{RESET}" if dry_run else f"{GREEN}[LIVE EXECUTION]{RESET}"
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}   PAPER TRADING REBALANCING CYCLE — {mode_str}   {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

        val = self.get_portfolio_valuation()
        total_port_val = val["total_value"]
        current_cash = val["cash"]
        min_cash_buffer = total_port_val * 0.05  # Keep at least 5% ($50 on $1k)
        max_pos_cap = total_port_val * 0.25      # Max 25% ($250 on $1k) per stock

        executed_actions = []

        # ─────────────────────────────────────────────────────────────
        # STEP 1: AUDIT & RESOLVE EXISTING POSITIONS (SELLS & TRIMS)
        # ─────────────────────────────────────────────────────────────
        held_syms = list(self.data["positions"].keys())
        audit_results = {}

        if held_syms:
            print(f"{BOLD}{CYAN}🔍 STEP 1: AUDITING HELD POSITIONS ({len(held_syms)} stocks)...{RESET}")

        for sym in held_syms:
            print(f"  • Auditing held position {BOLD}{sym}{RESET}...")
            r = audit_ticker(sym)
            if not r:
                continue
            audit_results[sym] = r

            pos = self.data["positions"][sym]
            shares = pos["shares"]
            price = r["price"]
            mkt_val = shares * price
            weight = (mkt_val / total_port_val) * 100.0

            q_score = r["quality_score"]
            v_score = r["valuation_score"]
            sig_code = r["screening_code"]

            # Update position metadata
            pos["last_score"] = r["reality_score"]
            pos["screening_code"] = sig_code

            # Check for full liquidation
            sell_reason = None
            if not r["quality_gate"] or q_score < 5.5:
                sell_reason = f"Quality gate failure (Quality: {q_score:.1f}/10 below 5.5 threshold)"
            elif sig_code in ["VALUE_TRAP", "FAIL_BOTH"]:
                sell_reason = f"Deteriorated into {sig_code} (Reality Score: {r['reality_score']:.2f})"
            elif r.get("persistent_ni_decline") and r.get("debt_accelerating"):
                sell_reason = "Compound Fundamental Deterioration (Earnings falling + Debt expanding)"

            if sell_reason:
                print(f"    {RED}🚨 SELL SIGNAL FOR {sym}: {sell_reason}{RESET}")
                dollar_amount = shares * price
                realized_pnl = dollar_amount - (shares * pos["cost_basis_per_share"])

                executed_actions.append({
                    "action": "SELL",
                    "ticker": sym,
                    "shares": shares,
                    "price": price,
                    "amount": dollar_amount,
                    "realized_pnl": realized_pnl,
                    "reason": sell_reason
                })

                if not dry_run:
                    current_cash += dollar_amount
                    self.data["cash"] = current_cash
                    del self.data["positions"][sym]
                    self.data["transactions"].append({
                        "timestamp": datetime.now().isoformat(),
                        "action": "SELL",
                        "ticker": sym,
                        "shares": shares,
                        "price": price,
                        "amount": dollar_amount,
                        "cash_after": current_cash,
                        "realized_pnl": realized_pnl,
                        "reason": sell_reason
                    })
                continue

            # Check for trimming (Weight > 28% or Expensive Quality > 15%)
            trim_target = None
            if weight > 28.0:
                trim_target = total_port_val * 0.22  # Trim down to 22%
                trim_reason = f"Rebalancing trim (Weight {weight:.1f}% exceeded 28.0% position cap)"
            elif sig_code == "EXPENSIVE_QUALITY" and weight > 16.0:
                trim_target = total_port_val * 0.14  # Trim down to 14%
                trim_reason = f"Valuation discipline trim (Valuation fell to {v_score:.1f}/10, trimming to 14%)"

            if trim_target and mkt_val > trim_target:
                excess_val = mkt_val - trim_target
                shares_to_trim = excess_val / price
                if excess_val >= 20.0:  # Only trim if worth at least $20
                    print(f"    {YELLOW}✂ TRIM SIGNAL FOR {sym}: {trim_reason} (Selling {shares_to_trim:.4f} shares / ${excess_val:.2f}){RESET}")
                    realized_pnl = excess_val - (shares_to_trim * pos["cost_basis_per_share"])

                    executed_actions.append({
                        "action": "TRIM",
                        "ticker": sym,
                        "shares": shares_to_trim,
                        "price": price,
                        "amount": excess_val,
                        "realized_pnl": realized_pnl,
                        "reason": trim_reason
                    })

                    if not dry_run:
                        current_cash += excess_val
                        pos["shares"] -= shares_to_trim
                        pos["total_cost"] = pos["shares"] * pos["cost_basis_per_share"]
                        self.data["cash"] = current_cash
                        self.data["transactions"].append({
                            "timestamp": datetime.now().isoformat(),
                            "action": "TRIM",
                            "ticker": sym,
                            "shares": shares_to_trim,
                            "price": price,
                            "amount": excess_val,
                            "cash_after": current_cash,
                            "realized_pnl": realized_pnl,
                            "reason": trim_reason
                        })

        # ─────────────────────────────────────────────────────────────
        # STEP 2: AUDIT WATCHLIST UNIVERSE & DISCOVER ENTRY CANDIDATES
        # ─────────────────────────────────────────────────────────────
        print(f"\n{BOLD}{CYAN}🔍 STEP 2: SCREENING WATCHLIST UNIVERSE ({len(self.data['watchlist'])} stocks)...{RESET}")

        candidate_pool = []
        for sym in self.data["watchlist"]:
            if sym in audit_results:
                r = audit_results[sym]
            else:
                print(f"  • Auditing {BOLD}{sym}{RESET}...")
                r = audit_ticker(sym)
                if not r:
                    continue
                audit_results[sym] = r

            # Check if passes all 3 Gates
            if r["quality_gate"] and r["valuation_gate"] and r["data_gate"]:
                code = r["screening_code"]
                if code in ["HIGH_CONVICTION", "BALANCED_PASS"]:
                    candidate_pool.append(r)

        # Sort candidates by composite Reality Score descending
        candidate_pool.sort(key=lambda x: x["reality_score"], reverse=True)

        print(f"\n  {GREEN}✔ Found {len(candidate_pool)} qualified candidates passing all 3 Hurdle Gates:{RESET}")
        for c in candidate_pool:
            print(f"    • {BOLD}{c['symbol']:<5}{RESET} Score: {c['reality_score']:.2f} (Q:{c['quality_score']:.1f}, V:{c['valuation_score']:.1f}) [{c['screening_code']}] — ${c['price']:.2f}")

        # ─────────────────────────────────────────────────────────────
        # STEP 3: CAPITAL ALLOCATION & POSITION SIZING (BUYS)
        # ─────────────────────────────────────────────────────────────
        print(f"\n{BOLD}{CYAN}🎯 STEP 3: ALLOCATING CAPITAL TO TOP CANDIDATES...{RESET}")
        available_cash_to_invest = max(0.0, current_cash - min_cash_buffer)
        print(f"  • Usable Cash (after 5% safety buffer of ${min_cash_buffer:.2f}): {BOLD}${available_cash_to_invest:,.2f}{RESET}")

        if available_cash_to_invest < 25.0:
            print(f"  {YELLOW}Insufficient usable cash (${available_cash_to_invest:.2f} < $25 min trade size) for new buys.{RESET}")
        else:
            # Calculate existing sector exposures
            val_after_sells = self.get_portfolio_valuation()
            current_positions = self.data["positions"]
            sector_exposures = val_after_sells["sector_weights"].copy()

            # Group candidates by sector for intra-sector proportional sizing
            sector_map = {}
            for cand in candidate_pool:
                sec = cand["sector"]
                sector_map.setdefault(sec, []).append(cand)

            def get_sector_cap_pct(sec):
                if sec == "Technology": return 0.40
                elif sec == "Financial Services": return 0.30
                elif sec == "Communication Services": return 0.22
                else: return 0.15

            # Calculate target dollar allocation per candidate
            target_allocations = {}
            for sec, cands in sector_map.items():
                sec_cap_dollars = total_port_val * get_sector_cap_pct(sec)
                total_score = sum(c["reality_score"] for c in cands)
                for cand in cands:
                    sym = cand["symbol"]
                    if len(cands) == 1:
                        target_pct = 0.16 if cand["screening_code"] == "HIGH_CONVICTION" else 0.10
                        target_allocations[sym] = min(total_port_val * target_pct, total_port_val * 0.20)
                    else:
                        # Intra-sector proportional slicing so no top performer is crowded out
                        prop_weight = cand["reality_score"] / total_score
                        target_allocations[sym] = min(sec_cap_dollars * prop_weight, total_port_val * 0.18)

            for cand in candidate_pool:
                if available_cash_to_invest < 25.0:
                    break

                sym = cand["symbol"]
                price = cand["price"]
                sector = cand["sector"]
                code = cand["screening_code"]

                target_dollars = target_allocations.get(sym, total_port_val * 0.12)
                current_held_val = 0.0
                if sym in current_positions:
                    current_held_val = current_positions[sym]["shares"] * price

                needed_dollars = target_dollars - current_held_val
                if needed_dollars < 25.0:
                    continue  # Already sufficiently weighted

                # Sector cap check
                current_sec_pct = sector_exposures.get(sector, 0.0)
                sec_cap_pct = get_sector_cap_pct(sector) * 100.0
                max_sec_room = (total_port_val * (sec_cap_pct / 100.0)) - (current_sec_pct / 100.0 * total_port_val)
                if max_sec_room < 25.0:
                    print(f"    {YELLOW}Skipping {sym} ({sector}): Sector limit reached ({current_sec_pct:.1f}% >= {sec_cap_pct:.1f}%){RESET}")
                    continue

                # Cap purchase size to available cash, position max, and remaining sector room
                buy_amount = min(needed_dollars, available_cash_to_invest, max_pos_cap, max_sec_room)
                shares_to_buy = buy_amount / price

                buy_reason = f"Passed Dual-Gate (Q:{cand['quality_score']:.1f}, V:{cand['valuation_score']:.1f}) — {code} (Intra-Sector Diversified)"
                print(f"    {GREEN}✔ BUY ORDER FOR {sym}: {shares_to_buy:.4f} shares @ ${price:.2f} = ${buy_amount:.2f} ({code}){RESET}")

                executed_actions.append({
                    "action": "BUY",
                    "ticker": sym,
                    "shares": shares_to_buy,
                    "price": price,
                    "amount": buy_amount,
                    "realized_pnl": 0.0,
                    "reason": buy_reason
                })

                available_cash_to_invest -= buy_amount
                current_cash -= buy_amount
                sector_exposures[sector] = sector_exposures.get(sector, 0.0) + (buy_amount / total_port_val * 100.0)

                if not dry_run:
                    self.data["cash"] = current_cash
                    if sym not in self.data["positions"]:
                        self.data["positions"][sym] = {
                            "shares": shares_to_buy,
                            "cost_basis_per_share": price,
                            "total_cost": buy_amount,
                            "first_bought_at": datetime.now().isoformat(),
                            "last_updated": datetime.now().isoformat(),
                            "last_score": cand["reality_score"],
                            "screening_code": code
                        }
                    else:
                        existing = self.data["positions"][sym]
                        new_total_cost = existing["total_cost"] + buy_amount
                        new_shares = existing["shares"] + shares_to_buy
                        existing["cost_basis_per_share"] = new_total_cost / new_shares
                        existing["total_cost"] = new_total_cost
                        existing["shares"] = new_shares
                        existing["last_updated"] = datetime.now().isoformat()
                        existing["last_score"] = cand["reality_score"]
                        existing["screening_code"] = code

                    self.data["transactions"].append({
                        "timestamp": datetime.now().isoformat(),
                        "action": "BUY",
                        "ticker": sym,
                        "shares": shares_to_buy,
                        "price": price,
                        "amount": buy_amount,
                        "cash_after": current_cash,
                        "realized_pnl": 0.0,
                        "reason": buy_reason
                    })

        # Save portfolio if live
        if not dry_run:
            self.save_portfolio()

        # ─────────────────────────────────────────────────────────────
        # STEP 4: CYCLE COMPLETION SUMMARY
        # ─────────────────────────────────────────────────────────────
        print(f"\n{BOLD}{CYAN}───────────────────────────────────────────────────────────────────────────────────────────{RESET}")
        print(f"{BOLD}CYCLE EXECUTION SUMMARY:{RESET} {len(executed_actions)} trades generated")
        if executed_actions:
            for act in executed_actions:
                col = GREEN if act["action"] == "BUY" else RED
                print(f"  • {col}{act['action']:<5}{RESET} {act['ticker']:<5} {act['shares']:>8.4f} shs @ ${act['price']:>7.2f} = ${act['amount']:>7.2f} | {act['reason']}")
        else:
            print(f"  • No rebalancing trades required. Portfolio is optimally aligned with current reality scores.")
        print(f"{BOLD}{CYAN}───────────────────────────────────────────────────────────────────────────────────────────{RESET}\n")

        # Show updated dashboard
        self.print_dashboard()


def main():
    parser = argparse.ArgumentParser(description="Autonomous Fact-Based Paper Trading Agent ($1,000 Starting Capital)")
    parser.add_argument("--run", action="store_true", help="Execute an autonomous screening & rebalancing cycle")
    parser.add_argument("--dry-run", action="store_true", help="Preview rebalancing trades without modifying state")
    parser.add_argument("--history", action="store_true", help="Display full paper trading transaction history")
    parser.add_argument("--reset", action="store_true", help="Reset portfolio back to initial $1,000.00 cash")
    parser.add_argument("--add", metavar="SYM", help="Add ticker symbol to universe watchlist")
    parser.add_argument("--remove", metavar="SYM", help="Remove ticker symbol from universe watchlist")
    parser.add_argument("--cash", type=float, help="Set custom cash balance on reset")

    args = parser.parse_args()
    mgr = PaperPortfolioManager()

    if args.reset:
        cash = args.cash if args.cash else 1000.00
        mgr.reset_portfolio(cash)
    elif args.add:
        mgr.add_to_watchlist(args.add)
    elif args.remove:
        mgr.remove_from_watchlist(args.remove)
    elif args.history:
        mgr.print_history()
    elif args.run:
        mgr.run_cycle(dry_run=False)
    elif args.dry_run:
        mgr.run_cycle(dry_run=True)
    else:
        mgr.print_dashboard()


if __name__ == "__main__":
    main()
