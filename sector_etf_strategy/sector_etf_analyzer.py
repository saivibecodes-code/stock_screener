#!/usr/bin/env python3
"""
Sector ETF Reality Analyzer (v1.0)
Institutional Sector ETF Relative Momentum, Technical Regime, Holdings Concentration & RRG Quadrant Engine.

Evaluates:
1. Relative Momentum vs S&P 500 (SPY) across 1M, 3M, 6M, and 12M intervals
2. Macro Technical Regime (Price vs 50-Day & 200-Day SMA, 14-Day RSI)
3. Institutional Holdings Concentration Risk (Top 5 / Top 10 weights)
4. RRG Quadrants: LEADING, WEAKENING, LAGGING, IMPROVING
5. Composite Sector Score (0-100) & Actionable Tactical Signals
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
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


class SectorETFAnalyzer:
    """Analyzes a Sector or Thematic ETF for relative momentum, regime, and structural concentration."""

    def __init__(self, ticker_symbol: str, benchmark_symbol: str = "SPY"):
        self.symbol = ticker_symbol.strip().upper()
        self.benchmark = benchmark_symbol.strip().upper()
        self.ticker = yf.Ticker(self.symbol)
        self.bench_ticker = yf.Ticker(self.benchmark)
        self.info = {}
        self.history = pd.DataFrame()
        self.bench_history = pd.DataFrame()
        self.top_holdings = []
        self.warnings = []

    def fetch_data(self) -> bool:
        """Fetches live quotes, 1-year historical prices, and fund holdings."""
        try:
            self.info = self.ticker.info or {}
            # Download 1 year + 40 days buffer for 200-day rolling indicators
            self.history = self.ticker.history(period="18mo")
            self.bench_history = self.bench_ticker.history(period="18mo")

            if self.history.empty or len(self.history) < 50:
                self.warnings.append("Insufficient price history available.")
                return False

            # Fetch top holdings if available
            fd = getattr(self.ticker, "funds_data", None)
            if fd:
                th = getattr(fd, "top_holdings", None)
                if th is not None and not th.empty:
                    for sym, row in th.iterrows():
                        self.top_holdings.append({
                            "symbol": str(sym),
                            "name": str(row.get("Name", sym)),
                            "weight_pct": float(row.get("Holding Percent", 0.0)) * 100.0
                        })
            return True
        except Exception as e:
            self.warnings.append(f"Data fetch error: {str(e)}")
            return False

    def calculate_technicals(self) -> dict:
        """Calculates 50d/200d SMA, RSI-14, and Trend Regime."""
        close = self.history["Close"].dropna()
        cur_px = float(close.iloc[-1])

        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else cur_px
        sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma_50

        dist_50_pct = ((cur_px / sma_50) - 1.0) * 100.0
        dist_200_pct = ((cur_px / sma_200) - 1.0) * 100.0

        # 14-day RSI
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        roll_gain = gain.rolling(14).mean()
        roll_loss = loss.rolling(14).mean()
        rs = roll_gain / roll_loss.replace(0, np.nan)
        rsi = float(100.0 - (100.0 / (1.0 + rs.iloc[-1]))) if not np.isnan(rs.iloc[-1]) else 50.0

        # Technical Trend Regime
        if cur_px >= sma_50 and sma_50 >= sma_200:
            regime = "STRONG_BULLISH"
        elif cur_px < sma_50 and cur_px >= sma_200:
            regime = "BULLISH_PULLBACK"
        elif cur_px >= sma_50 and cur_px < sma_200:
            regime = "BEARISH_RECOVERY"
        else:
            regime = "STRONG_BEARISH"

        return {
            "current_price": cur_px,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "dist_50_pct": dist_50_pct,
            "dist_200_pct": dist_200_pct,
            "rsi_14": rsi,
            "regime": regime
        }

    def calculate_relative_momentum(self) -> dict:
        """Calculates relative momentum spreads vs SPY across 1M, 3M, 6M, and 12M."""
        etf_c = self.history["Close"].dropna()
        spy_c = self.bench_history["Close"].dropna()

        # Align series by matching dates
        df = pd.DataFrame({"ETF": etf_c, "SPY": spy_c}).dropna()

        def get_ret(series, days):
            if len(series) > days:
                return (series.iloc[-1] / series.iloc[-days]) - 1.0
            elif len(series) > 5:
                return (series.iloc[-1] / series.iloc[0]) - 1.0
            return 0.0

        # Approximate trading days
        r_1m_etf = get_ret(df["ETF"], 21)
        r_1m_spy = get_ret(df["SPY"], 21)
        spread_1m = (r_1m_etf - r_1m_spy) * 100.0

        r_3m_etf = get_ret(df["ETF"], 63)
        r_3m_spy = get_ret(df["SPY"], 63)
        spread_3m = (r_3m_etf - r_3m_spy) * 100.0

        r_6m_etf = get_ret(df["ETF"], 126)
        r_6m_spy = get_ret(df["SPY"], 126)
        spread_6m = (r_6m_etf - r_6m_spy) * 100.0

        r_12m_etf = get_ret(df["ETF"], 252)
        r_12m_spy = get_ret(df["SPY"], 252)
        spread_12m = (r_12m_etf - r_12m_spy) * 100.0

        # RRG Quadrant Proxy (Relative Strength Ratio & Momentum)
        # RS-Ratio = 100 + ((Price_ETF / Price_SPY) - 50d_Mean) / 50d_Std * 5
        ratio_series = df["ETF"] / df["SPY"]
        roll_mean = ratio_series.rolling(50).mean()
        roll_std = ratio_series.rolling(50).std().replace(0, np.nan)
        z_score = (ratio_series - roll_mean) / roll_std
        rs_ratio = float(100.0 + (z_score.iloc[-1] * 5.0)) if not np.isnan(z_score.iloc[-1]) else 100.0

        # RS-Momentum = 14-day rate of change of RS-Ratio
        rs_mom_delta = float(z_score.iloc[-1] - z_score.iloc[-14]) if len(z_score) >= 14 else 0.0
        rs_momentum = 100.0 + (rs_mom_delta * 5.0)

        # Classify RRG Quadrant
        if rs_ratio >= 100.0 and rs_momentum >= 100.0:
            rrg_quadrant = "LEADING"        # Outperforming with accelerating momentum
        elif rs_ratio >= 100.0 and rs_momentum < 100.0:
            rrg_quadrant = "WEAKENING"      # Outperforming, but momentum slowing
        elif rs_ratio < 100.0 and rs_momentum < 100.0:
            rrg_quadrant = "LAGGING"        # Underperforming with decelerating momentum
        else:
            rrg_quadrant = "IMPROVING"      # Underperforming, but momentum inflecting up

        return {
            "ret_1m_etf": r_1m_etf * 100.0,
            "ret_1m_spy": r_1m_spy * 100.0,
            "spread_1m": spread_1m,
            "ret_3m_etf": r_3m_etf * 100.0,
            "ret_3m_spy": r_3m_spy * 100.0,
            "spread_3m": spread_3m,
            "ret_6m_etf": r_6m_etf * 100.0,
            "ret_6m_spy": r_6m_spy * 100.0,
            "spread_6m": spread_6m,
            "ret_12m_etf": r_12m_etf * 100.0,
            "ret_12m_spy": r_12m_spy * 100.0,
            "spread_12m": spread_12m,
            "rs_ratio": rs_ratio,
            "rs_momentum": rs_momentum,
            "rrg_quadrant": rrg_quadrant
        }

    def calculate_concentration_and_fundamentals(self) -> dict:
        """Analyzes top holdings concentration risk, valuation, and AUM."""
        top3_weight = sum(h["weight_pct"] for h in self.top_holdings[:3])
        top5_weight = sum(h["weight_pct"] for h in self.top_holdings[:5])
        top10_weight = sum(h["weight_pct"] for h in self.top_holdings[:10])

        top_single = self.top_holdings[0] if self.top_holdings else {"symbol": "N/A", "weight_pct": 0.0}

        # Concentration Risk Flag
        concentration_risk = "LOW"
        if top_single["weight_pct"] >= 18.0 or top3_weight >= 40.0:
            concentration_risk = "HIGH"
            self.warnings.append(f"High concentration: Top single holding ({top_single['symbol']}) is {top_single['weight_pct']:.1f}%")
        elif top_single["weight_pct"] >= 12.0 or top3_weight >= 30.0:
            concentration_risk = "MODERATE"

        # AUM & Volume
        total_assets = self.info.get("totalAssets") or self.info.get("netAssets") or 0.0
        aum_billions = total_assets / 1e9 if total_assets > 0 else 0.0

        pe_ratio = self.info.get("trailingPE", None)
        div_yield = self.info.get("yield") or self.info.get("dividendYield") or 0.0
        if div_yield < 0.20:
            div_yield_pct = div_yield * 100.0
        else:
            div_yield_pct = div_yield

        expense_ratio = self.info.get("annualReportExpenseRatio", 0.09) or 0.09
        if expense_ratio < 0.05:
            expense_ratio_pct = expense_ratio * 100.0
        else:
            expense_ratio_pct = expense_ratio

        return {
            "top_single": top_single,
            "top3_weight": top3_weight,
            "top5_weight": top5_weight,
            "top10_weight": top10_weight,
            "concentration_risk": concentration_risk,
            "aum_billions": aum_billions,
            "pe_ratio": pe_ratio,
            "dividend_yield_pct": div_yield_pct,
            "expense_ratio_pct": expense_ratio_pct
        }

    def analyze(self) -> dict:
        """Executes full institutional audit of the Sector ETF and computes Composite Score."""
        if not self.fetch_data():
            return {
                "symbol": self.symbol,
                "name": self.info.get("shortName", self.symbol),
                "status": "DATA_ERROR",
                "composite_score": 0.0,
                "action": "AVOID",
                "warnings": self.warnings
            }

        tech = self.calculate_technicals()
        rel_mom = self.calculate_relative_momentum()
        fund = self.calculate_concentration_and_fundamentals()

        # ----------------------------------------------------
        # COMPOSITE SECTOR SCORING (0 to 100 Scale)
        # ----------------------------------------------------
        score = 50.0  # Base neutral

        # 1. Relative Momentum vs SPY (Max +/- 30 pts)
        # Weighted: 1M (25%), 3M (35%), 6M (25%), 12M (15%)
        mom_blend = (
            rel_mom["spread_1m"] * 0.25 +
            rel_mom["spread_3m"] * 0.35 +
            rel_mom["spread_6m"] * 0.25 +
            rel_mom["spread_12m"] * 0.15
        )
        # Clamp mom adjustment between -30 and +30
        score += max(-30.0, min(30.0, mom_blend * 1.5))

        # 2. Technical Trend Regime (Max +/- 15 pts)
        regime_weights = {
            "STRONG_BULLISH": +15.0,
            "BULLISH_PULLBACK": +8.0,
            "BEARISH_RECOVERY": -5.0,
            "STRONG_BEARISH": -15.0
        }
        score += regime_weights.get(tech["regime"], 0.0)

        # 3. RRG Quadrant Bonus / Penalty (Max +/- 10 pts)
        rrg_weights = {
            "LEADING": +10.0,
            "IMPROVING": +5.0,
            "WEAKENING": -3.0,
            "LAGGING": -10.0
        }
        score += rrg_weights.get(rel_mom["rrg_quadrant"], 0.0)

        # 4. RSI Sweet Spot (45 to 68 is bullish momentum without extreme overbought)
        rsi = tech["rsi_14"]
        if 50.0 <= rsi <= 68.0:
            score += 5.0
        elif rsi > 75.0:
            score -= 4.0  # Overheated
        elif rsi < 32.0:
            score += 2.0  # Oversold mean-reversion potential

        # 5. Concentration Penalty
        if fund["concentration_risk"] == "HIGH":
            score -= 5.0

        final_score = max(0.0, min(100.0, score))

        # Action Recommendation
        if final_score >= 75.0 and rel_mom["rrg_quadrant"] in ["LEADING", "IMPROVING"]:
            action = "STRONG_OVERWEIGHT"
        elif final_score >= 60.0:
            action = "OVERWEIGHT"
        elif final_score >= 45.0:
            action = "NEUTRAL"
        elif final_score >= 35.0:
            action = "UNDERWEIGHT"
        else:
            action = "AVOID"

        return {
            "symbol": self.symbol,
            "name": self.info.get("shortName", self.symbol),
            "category": self.info.get("category", "Sector ETF"),
            "technicals": tech,
            "relative_momentum": rel_mom,
            "fundamentals": fund,
            "top_holdings": self.top_holdings[:10],
            "composite_score": round(final_score, 1),
            "action": action,
            "warnings": self.warnings
        }

    def print_report(self, audit: dict):
        """Prints rich terminal audit report."""
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}             SECTOR ETF REALITY AUDIT: {audit['symbol']} ({audit['name']})                       {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

        t = audit["technicals"]
        rm = audit["relative_momentum"]
        f = audit["fundamentals"]

        action_colors = {
            "STRONG_OVERWEIGHT": GREEN,
            "OVERWEIGHT": CYAN,
            "NEUTRAL": YELLOW,
            "UNDERWEIGHT": MAGENTA,
            "AVOID": RED
        }
        act_col = action_colors.get(audit["action"], WHITE)

        print(f"{BOLD}Market Price:{RESET}        ${t['current_price']:.2f}")
        print(f"{BOLD}AUM / Fee:{RESET}           ${f['aum_billions']:.2f}B | Expense Ratio: {f['expense_ratio_pct']:.2f}%")
        print(f"{BOLD}P/E & Yield:{RESET}         P/E: {f['pe_ratio'] if f['pe_ratio'] else 'N/A'} | Div Yield: {f['dividend_yield_pct']:.2f}%")
        print(f"{BOLD}Composite Score:{RESET}     {BOLD}{act_col}{audit['composite_score']}/100{RESET} ──► {BOLD}{act_col}[{audit['action']}]{RESET}")

        # Technical & Regime
        print(f"\n{CYAN}--- TECHNICAL REGIME & MOVING AVERAGES ---{RESET}")
        reg_col = GREEN if "BULLISH" in t["regime"] else RED
        print(f"  • Trend State:             {reg_col}{t['regime']}{RESET}")
        print(f"  • 50-Day SMA:              ${t['sma_50']:.2f} ({t['dist_50_pct']:+.2f}%)")
        print(f"  • 200-Day SMA:             ${t['sma_200']:.2f} ({t['dist_200_pct']:+.2f}%)")
        rsi_col = YELLOW if t["rsi_14"] > 70 or t["rsi_14"] < 30 else GREEN
        print(f"  • 14-Day RSI:              {rsi_col}{t['rsi_14']:.1f}{RESET}")

        # Relative Momentum vs SPY
        print(f"\n{CYAN}--- RELATIVE MOMENTUM VS S&P 500 (SPY) ---{RESET}")
        rrg_col = GREEN if rm["rrg_quadrant"] == "LEADING" else (CYAN if rm["rrg_quadrant"] == "IMPROVING" else (YELLOW if rm["rrg_quadrant"] == "WEAKENING" else RED))
        print(f"  • RRG Quadrant:            {BOLD}{rrg_col}[{rm['rrg_quadrant']}]{RESET} (RS-Ratio: {rm['rs_ratio']:.1f} | RS-Mom: {rm['rs_momentum']:.1f})")

        def fmt_spread(val):
            return f"{GREEN}{val:>+6.2f}%{RESET}" if val >= 0 else f"{RED}{val:>+6.2f}%{RESET}"

        print(f"  • 1-Month Spread vs SPY:   {fmt_spread(rm['spread_1m'])} (ETF: {rm['ret_1m_etf']:+.2f}% vs SPY: {rm['ret_1m_spy']:+.2f}%)")
        print(f"  • 3-Month Spread vs SPY:   {fmt_spread(rm['spread_3m'])} (ETF: {rm['ret_3m_etf']:+.2f}% vs SPY: {rm['ret_3m_spy']:+.2f}%)")
        print(f"  • 6-Month Spread vs SPY:   {fmt_spread(rm['spread_6m'])} (ETF: {rm['ret_6m_etf']:+.2f}% vs SPY: {rm['ret_6m_spy']:+.2f}%)")
        print(f"  • 12-Month Spread vs SPY:  {fmt_spread(rm['spread_12m'])} (ETF: {rm['ret_12m_etf']:+.2f}% vs SPY: {rm['ret_12m_spy']:+.2f}%)")

        # Top Holdings
        if audit["top_holdings"]:
            print(f"\n{CYAN}--- TOP HOLDINGS & CONCENTRATION PROFILE ---{RESET}")
            conc_col = GREEN if f["concentration_risk"] == "LOW" else (YELLOW if f["concentration_risk"] == "MODERATE" else RED)
            print(f"  • Concentration Risk:      {conc_col}{f['concentration_risk']}{RESET} (Top 3: {f['top3_weight']:.1f}% | Top 5: {f['top5_weight']:.1f}% | Top 10: {f['top10_weight']:.1f}%)")
            print(f"  • Top Component Holdings:")
            for h in audit["top_holdings"][:5]:
                print(f"     - {BOLD}{h['symbol']:<6}{RESET} ({h['name'][:22]:<24}): {h['weight_pct']:>5.2f}%")

        if audit["warnings"]:
            print(f"\n{YELLOW}Audit Alerts:{RESET}")
            for w in audit["warnings"]:
                print(f"  • {w}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Sector ETF Reality Analyzer")
    parser.add_argument("ticker", help="Sector ETF ticker (e.g. XLK, XLF, XLE, XLV, SMH)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    analyzer = SectorETFAnalyzer(args.ticker)
    res = analyzer.analyze()

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        analyzer.print_report(res)


if __name__ == "__main__":
    main()
