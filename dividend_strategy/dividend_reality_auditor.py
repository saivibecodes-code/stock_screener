#!/usr/bin/env python3
"""
Dividend Reality Auditor (v1.0)
Institutional Dividend Safety, Growth & Cash Flow Coverage Engine.

Evaluates dividend durability by auditing audited financial statements:
1. Free Cash Flow (FCF) Payout Ratio (Dividends Paid / FCF)
2. Dividend Streak & 1Y/3Y/5Y Dividend CAGR
3. The Chowder Rule (Yield + 5Y Dividend CAGR)
4. Balance Sheet Fortress (Net Debt / EBITDA, Interest Coverage, Altman Z'')
5. Dividend Safety Score (0-100) & Institutional Conviction Tiers:
   - DIVIDEND_FORTRESS (Score >= 85)
   - SAFE_COMPOUNDER   (Score 70-84)
   - MODERATE_RISK     (Score 50-69)
   - YIELD_TRAP        (Score < 50)
"""

import os
import sys
import json
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


class DividendRealityAuditor:
    """Audits dividend sustainability, cash flow coverage, and growth metrics."""

    def __init__(self, ticker_symbol: str):
        self.symbol = ticker_symbol.strip().upper()
        self.ticker = yf.Ticker(self.symbol)
        self.info = {}
        self.cashflow = pd.DataFrame()
        self.financials = pd.DataFrame()
        self.balance_sheet = pd.DataFrame()
        self.dividends = pd.Series(dtype=float)
        self.data_confidence = 100
        self.warnings = []

    def fetch_data(self) -> bool:
        """Fetches live corporate financials and historical dividend distributions."""
        try:
            self.info = self.ticker.info or {}
            self.cashflow = self.ticker.cashflow
            self.financials = self.ticker.financials
            self.balance_sheet = self.ticker.balance_sheet
            self.dividends = self.ticker.dividends

            if not self.info or (self.cashflow.empty and self.financials.empty):
                return False
            return True
        except Exception as e:
            self.warnings.append(f"Data fetch error: {str(e)}")
            return False

    def get_first_available_row(self, df: pd.DataFrame, candidate_names: list):
        """Extracts the first matching accounting line item across naming variations."""
        if df is None or df.empty:
            return None
        for name in candidate_names:
            for idx in df.index:
                if str(idx).strip().lower() == name.strip().lower():
                    row = df.loc[idx].dropna()
                    if not row.empty:
                        return row
        return None

    def analyze_dividend_history(self) -> dict:
        """Analyzes historical dividend payments, streaks, and CAGRs."""
        res = {
            "has_dividends": False,
            "annual_payouts": {},
            "streak_years": 0,
            "cagr_1y": 0.0,
            "cagr_3y": 0.0,
            "cagr_5y": 0.0,
            "cut_in_last_5y": False,
            "is_aristocrat": False,
            "is_king": False,
            "payout_frequency": "Quarterly"
        }

        if self.dividends.empty:
            return res

        # Check frequency using median days between recent dividend dates
        if len(self.dividends) >= 3:
            day_diffs = self.dividends.index.to_series().diff().dt.days.dropna().tail(6)
            med_days = day_diffs.median() if not day_diffs.empty else 90
            if med_days <= 45:
                res["payout_frequency"] = "Monthly"
            elif med_days <= 120:
                res["payout_frequency"] = "Quarterly"
            elif med_days <= 220:
                res["payout_frequency"] = "Semi-Annual"
            else:
                res["payout_frequency"] = "Annual"
        else:
            res["payout_frequency"] = "Quarterly"

        # Group dividends by calendar year
        yearly = self.dividends.groupby(self.dividends.index.year).sum()
        if yearly.empty:
            return res

        res["has_dividends"] = True
        res["annual_payouts"] = {int(k): float(v) for k, v in yearly.items()}

        cur_year = datetime.now().year
        full_years = yearly[yearly.index < cur_year]

        # Check for per-share payout cut in last 5 years
        # Using actual per-share distribution drops > 5% to avoid calendar ex-date timing anomalies
        cutoff_date = (datetime.now() - pd.Timedelta(days=5 * 365.25)).strftime("%Y-%m-%d")
        recent_divs_5y = self.dividends[cutoff_date:]
        if len(recent_divs_5y) >= 2:
            for i in range(1, len(recent_divs_5y)):
                prev_p = recent_divs_5y.iloc[i - 1]
                curr_p = recent_divs_5y.iloc[i]
                if curr_p < (prev_p * 0.93):  # Significant drop > 7%
                    res["cut_in_last_5y"] = True
                    break

        # Calculate annual run-rates using maximum quarterly/monthly payment per year
        yearly_max = self.dividends.groupby(self.dividends.index.year).max()
        full_years_max = yearly_max[yearly_max.index < cur_year]

        # Calculate streak using yearly max payment rate
        if len(full_years_max) >= 2:
            streak = 0
            m_vals = full_years_max.values
            for i in range(len(m_vals) - 1, 0, -1):
                if m_vals[i] >= m_vals[i - 1] * 0.999:
                    streak += 1
                else:
                    break
            res["streak_years"] = streak

        # Calculate CAGRs using full years
        if len(full_years) >= 2:
            vals = full_years.values
            latest_full = vals[-1]
            if len(vals) >= 2 and vals[-2] > 0:
                res["cagr_1y"] = (latest_full / vals[-2]) - 1.0

            if len(vals) >= 4 and vals[-4] > 0:
                res["cagr_3y"] = (latest_full / vals[-4]) ** (1.0 / 3.0) - 1.0

            if len(vals) >= 6 and vals[-6] > 0:
                res["cagr_5y"] = (latest_full / vals[-6]) ** (1.0 / 5.0) - 1.0
            elif len(vals) >= 3 and vals[0] > 0:
                span = len(vals) - 1
                res["cagr_5y"] = (latest_full / vals[0]) ** (1.0 / span) - 1.0

        # Verified Aristocrats & Kings Registry
        DIVIDEND_KINGS = {
            "DOV", "GWW", "PG", "MMM", "EMR", "KO", "JNJ", "CL", "CINF", "LOW",
            "LANC", "NDSN", "ITW", "HRL", "ABM", "SWK", "PH", "FRT", "AWR", "SJW"
        }
        DIVIDEND_ARISTOCRATS = {
            "ABBV", "CVX", "CAT", "TROW", "SYY", "BDX", "MO", "AFL", "CB", "GILD",
            "MDT", "GD", "NOC", "SHW", "APD", "ECL", "LIN", "CTAS", "ROP", "WMT",
            "SPGI", "MCO", "O", "IBM", "TXN", "PEP", "AMGN", "EXPD", "CHRW"
        }

        if self.symbol in DIVIDEND_KINGS or res["streak_years"] >= 50:
            res["is_king"] = True
            res["is_aristocrat"] = True
            res["streak_years"] = max(res["streak_years"], 50)
        elif self.symbol in DIVIDEND_ARISTOCRATS or res["streak_years"] >= 25:
            res["is_aristocrat"] = True
            res["streak_years"] = max(res["streak_years"], 25)

        return res

    def calculate_coverage_and_debt(self) -> dict:
        """Calculates FCF Payout Ratio, GAAP Payout Ratio, and Balance Sheet Health."""
        coverage = {
            "fcf": 0.0,
            "dividends_paid": 0.0,
            "fcf_payout_ratio": None,
            "gaap_payout_ratio": None,
            "net_debt": 0.0,
            "ebitda": 0.0,
            "net_debt_ebitda": None,
            "interest_coverage": None,
            "altman_z": 3.0,
            "sector": self.info.get("sector", "Unknown"),
            "industry": self.info.get("industry", "Unknown")
        }

        # 1. Free Cash Flow
        fcf_row = self.get_first_available_row(self.cashflow, ["Free Cash Flow", "FreeCashFlow"])
        if fcf_row is not None and len(fcf_row) > 0:
            coverage["fcf"] = float(fcf_row.iloc[0])
        else:
            # FCF = OCF - CapEx
            ocf_row = self.get_first_available_row(self.cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
            capex_row = self.get_first_available_row(self.cashflow, ["Capital Expenditure", "CapitalExpenditure"])
            if ocf_row is not None and capex_row is not None:
                ocf = float(ocf_row.iloc[0])
                capex = abs(float(capex_row.iloc[0]))
                coverage["fcf"] = ocf - capex

        # 2. Dividends Paid (Cashflow)
        div_row = self.get_first_available_row(self.cashflow, [
            "Cash Dividends Paid",
            "Common Stock Dividend Paid",
            "Dividends Paid",
            "Payment Of Dividends"
        ])
        if div_row is not None and len(div_row) > 0:
            coverage["dividends_paid"] = abs(float(div_row.iloc[0]))
        else:
            # Fallback to info dividendRate * sharesOutstanding
            rate = self.info.get("dividendRate", 0.0) or 0.0
            shares = self.info.get("sharesOutstanding", 0.0) or 0.0
            if rate > 0 and shares > 0:
                coverage["dividends_paid"] = rate * shares

        # FCF Payout Ratio
        if coverage["fcf"] > 0 and coverage["dividends_paid"] > 0:
            coverage["fcf_payout_ratio"] = coverage["dividends_paid"] / coverage["fcf"]
        elif coverage["fcf"] <= 0 and coverage["dividends_paid"] > 0:
            coverage["fcf_payout_ratio"] = 9.99  # Critical: negative FCF covering dividends!

        # GAAP Payout Ratio from info
        payout_info = self.info.get("payoutRatio", None)
        if payout_info is not None and not np.isnan(payout_info):
            coverage["gaap_payout_ratio"] = float(payout_info)

        # 3. Balance Sheet & Leverage
        total_debt = self.info.get("totalDebt", 0.0) or 0.0
        total_cash = self.info.get("totalCash", 0.0) or 0.0
        coverage["net_debt"] = max(0.0, total_debt - total_cash)

        ebitda = self.info.get("ebitda", 0.0) or 0.0
        coverage["ebitda"] = ebitda
        if ebitda > 0:
            coverage["net_debt_ebitda"] = coverage["net_debt"] / ebitda

        # Interest Coverage
        ebit_row = self.get_first_available_row(self.financials, ["EBIT", "Operating Income", "OperatingIncome"])
        interest_row = self.get_first_available_row(self.financials, ["Interest Expense", "InterestExpenseNonOperating"])
        if ebit_row is not None and interest_row is not None:
            ebit = abs(float(ebit_row.iloc[0]))
            interest = abs(float(interest_row.iloc[0]))
            if interest > 0:
                coverage["interest_coverage"] = ebit / interest

        # Altman Z-Score estimate
        total_assets_row = self.get_first_available_row(self.balance_sheet, ["Total Assets", "TotalAssets"])
        total_liab_row = self.get_first_available_row(self.balance_sheet, ["Total Liabilities Net Minority Interest", "TotalLiabilities"])
        re_row = self.get_first_available_row(self.balance_sheet, ["Retained Earnings", "RetainedEarnings"])
        wc_row = self.get_first_available_row(self.balance_sheet, ["Working Capital", "WorkingCapital"])

        if total_assets_row is not None and total_liab_row is not None:
            ta = float(total_assets_row.iloc[0])
            tl = float(total_liab_row.iloc[0])
            if ta > 0:
                wc = float(wc_row.iloc[0]) if wc_row is not None else 0.0
                re = float(re_row.iloc[0]) if re_row is not None else 0.0
                ebit = float(ebit_row.iloc[0]) if ebit_row is not None else 0.0
                book_eq = ta - tl

                z = (6.56 * (wc / ta)) + (3.26 * (re / ta)) + (6.72 * (ebit / ta)) + (1.05 * (book_eq / max(1.0, tl)))
                coverage["altman_z"] = max(0.0, z)

        return coverage

    def audit(self) -> dict:
        """Performs full institutional dividend audit and generates safety score (0-100)."""
        if not self.fetch_data():
            return {
                "symbol": self.symbol,
                "name": self.info.get("shortName", self.symbol),
                "status": "DATA_ERROR",
                "safety_score": 0.0,
                "tier": "CRITERIA_FAILS"
            }

        history = self.analyze_dividend_history()
        coverage = self.calculate_coverage_and_debt()

        current_price = self.info.get("currentPrice") or self.info.get("regularMarketPrice") or 0.0
        dividend_rate = self.info.get("dividendRate", 0.0) or 0.0
        dividend_yield = self.info.get("dividendYield", 0.0) or 0.0

        # Handle yield scale (yfinance can return 0.035 or 3.5)
        if dividend_yield is not None:
            if dividend_yield < 0.20:
                dividend_yield_pct = dividend_yield * 100.0
            else:
                dividend_yield_pct = dividend_yield
        else:
            dividend_yield_pct = (dividend_rate / current_price * 100.0) if current_price > 0 else 0.0

        five_yr_avg_yield = self.info.get("fiveYearAvgDividendYield", 0.0) or 0.0

        # 1. Chowder Number = Yield % + 5Y Dividend CAGR %
        cagr_5y_pct = history["cagr_5y"] * 100.0
        chowder_number = dividend_yield_pct + cagr_5y_pct

        # ----------------------------------------------------
        # DIVIDEND SAFETY SCORING ENGINE (0 to 100 Points)
        # ----------------------------------------------------
        score = 0.0

        # A. FCF Coverage (Max 30 points)
        fcf_payout = coverage["fcf_payout_ratio"]
        is_reit = coverage["sector"] == "Real Estate"

        if fcf_payout is None:
            # Fallback to GAAP payout
            gaap_p = coverage["gaap_payout_ratio"]
            if gaap_p is not None:
                if gaap_p <= 0.50:
                    score += 25.0
                elif gaap_p <= 0.70:
                    score += 20.0
                elif gaap_p <= 0.85:
                    score += 12.0
                else:
                    score += 4.0
            else:
                score += 15.0
        elif is_reit:
            # REITs legally must pay >= 90% taxable income, higher payout is standard
            if fcf_payout <= 0.75:
                score += 30.0
            elif fcf_payout <= 0.85:
                score += 25.0
            elif fcf_payout <= 0.95:
                score += 18.0
            elif fcf_payout <= 1.05:
                score += 10.0
            else:
                score += 0.0  # Dilution / debt funding
        else:
            # Standard Corporations
            if fcf_payout <= 0.40:
                score += 30.0
            elif fcf_payout <= 0.55:
                score += 26.0
            elif fcf_payout <= 0.70:
                score += 21.0
            elif fcf_payout <= 0.80:
                score += 16.0
            elif fcf_payout <= 0.90:
                score += 10.0
            else:
                score += 0.0  # Critical coverage failure

        # B. Dividend Growth Streak & Track Record (Max 25 points)
        streak = history["streak_years"]
        if history["is_king"]:
            score += 25.0
        elif history["is_aristocrat"]:
            score += 23.0
        elif streak >= 15:
            score += 19.0
        elif streak >= 10:
            score += 15.0
        elif streak >= 5:
            score += 10.0
        elif streak >= 2:
            score += 5.0

        # Penalty for recent dividend cut (-35 points)
        if history["cut_in_last_5y"]:
            score -= 35.0
            self.warnings.append("Recent dividend cut detected within past 5 years!")

        # C. 5-Year Dividend CAGR & Inflation Beat (Max 15 points)
        if cagr_5y_pct >= 8.0:
            score += 15.0
        elif cagr_5y_pct >= 5.0:
            score += 12.0
        elif cagr_5y_pct >= 3.0:
            score += 8.0
        elif cagr_5y_pct >= 1.0:
            score += 4.0
        else:
            score += 0.0

        # D. Balance Sheet Fortification (Max 15 points)
        nd_ebitda = coverage["net_debt_ebitda"]
        if is_reit:
            if nd_ebitda is not None:
                if nd_ebitda <= 5.5:
                    score += 10.0
                elif nd_ebitda <= 6.5:
                    score += 7.0
                elif nd_ebitda <= 7.5:
                    score += 4.0
                else:
                    score += 1.0
            else:
                score += 7.0
            score += 4.0  # Neutral property collateral adjustment
        else:
            if nd_ebitda is not None:
                if nd_ebitda <= 1.5:
                    score += 10.0
                elif nd_ebitda <= 2.5:
                    score += 7.0
                elif nd_ebitda <= 3.5:
                    score += 4.0
                else:
                    score += 0.0
            else:
                score += 6.0  # Neutral for financials

            z = coverage["altman_z"]
            if z >= 2.9:
                score += 5.0
            elif z >= 2.0:
                score += 3.0
            elif z < 1.2:
                score -= 5.0  # Distress hazard

        # E. Chowder Rule Attractiveness (Max 15 points)
        # Target: >= 10-12% for normal, >= 8% for high yielders (>3.5%)
        if dividend_yield_pct >= 3.5:
            if chowder_number >= 10.0:
                score += 15.0
            elif chowder_number >= 8.0:
                score += 11.0
            elif chowder_number >= 6.0:
                score += 7.0
            else:
                score += 2.0
        else:
            if chowder_number >= 12.0:
                score += 15.0
            elif chowder_number >= 9.0:
                score += 11.0
            elif chowder_number >= 6.0:
                score += 6.0
            else:
                score += 2.0

        # Clamping
        final_score = max(0.0, min(100.0, score))

        # Determine Institutional Tier
        if final_score >= 85.0 and not history["cut_in_last_5y"] and (fcf_payout is None or fcf_payout <= 0.75):
            tier = "DIVIDEND_FORTRESS"
        elif final_score >= 70.0 and not history["cut_in_last_5y"]:
            tier = "SAFE_COMPOUNDER"
        elif final_score >= 50.0:
            tier = "MODERATE_RISK"
        else:
            tier = "YIELD_TRAP"

        # Gate Check: Must have Safety Score >= 70 to qualify for portfolio inclusion
        passed_gates = (final_score >= 70.0) and not history["cut_in_last_5y"]

        return {
            "symbol": self.symbol,
            "name": self.info.get("shortName", self.symbol),
            "sector": coverage["sector"],
            "industry": coverage["industry"],
            "price": current_price,
            "dividend_rate": dividend_rate,
            "dividend_yield_pct": dividend_yield_pct,
            "five_yr_avg_yield": five_yr_avg_yield,
            "fcf_payout_ratio": fcf_payout,
            "gaap_payout_ratio": coverage["gaap_payout_ratio"],
            "streak_years": history["streak_years"],
            "cagr_1y_pct": history["cagr_1y"] * 100.0,
            "cagr_3y_pct": history["cagr_3y"] * 100.0,
            "cagr_5y_pct": cagr_5y_pct,
            "chowder_number": chowder_number,
            "payout_frequency": history["payout_frequency"],
            "is_aristocrat": history["is_aristocrat"],
            "is_king": history["is_king"],
            "cut_in_last_5y": history["cut_in_last_5y"],
            "net_debt_ebitda": coverage["net_debt_ebitda"],
            "altman_z": coverage["altman_z"],
            "safety_score": round(final_score, 1),
            "tier": tier,
            "passed_gates": passed_gates,
            "warnings": self.warnings
        }

    def print_report(self, audit: dict):
        """Prints a rich terminal report of the dividend audit."""
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{WHITE}             DIVIDEND REALITY AUDIT: {audit['symbol']} ({audit['name']})                 {RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════{RESET}\n")

        tier_colors = {
            "DIVIDEND_FORTRESS": GREEN,
            "SAFE_COMPOUNDER": CYAN,
            "MODERATE_RISK": YELLOW,
            "YIELD_TRAP": RED
        }
        t_col = tier_colors.get(audit["tier"], WHITE)

        badge = ""
        if audit["is_king"]:
            badge = f" {BOLD}{MAGENTA}[DIVIDEND KING - 50+ Yrs]{RESET}"
        elif audit["is_aristocrat"]:
            badge = f" {BOLD}{CYAN}[DIVIDEND ARISTOCRAT - 25+ Yrs]{RESET}"

        print(f"{BOLD}Sector / Industry:{RESET}   {audit['sector']} | {audit['industry']}")
        print(f"{BOLD}Market Price:{RESET}        ${audit['price']:.2f}")
        print(f"{BOLD}Dividend Yield:{RESET}      {audit['dividend_yield_pct']:.2f}% (Annual Rate: ${audit['dividend_rate']:.2f})")
        print(f"{BOLD}Payout Frequency:{RESET}    {audit['payout_frequency']}")
        print(f"{BOLD}Safety Score:{RESET}        {BOLD}{t_col}{audit['safety_score']}/100{RESET} ──► {BOLD}{t_col}[{audit['tier']}]{RESET}{badge}")

        print(f"\n{CYAN}--- CASH FLOW & COVERAGE INTEGRITY ---{RESET}")
        fcf_p = audit["fcf_payout_ratio"]
        if fcf_p is not None:
            fcf_str = f"{fcf_p * 100.0:.1f}%"
            fcf_col = GREEN if fcf_p <= 0.65 else (YELLOW if fcf_p <= 0.85 else RED)
            print(f"  • FCF Payout Ratio:        {fcf_col}{fcf_str}{RESET} (Dividends paid out of real Free Cash Flow)")
        else:
            print("  • FCF Payout Ratio:        N/A")

        gaap_p = audit["gaap_payout_ratio"]
        if gaap_p is not None:
            print(f"  • GAAP EPS Payout Ratio:   {gaap_p * 100.0:.1f}%")

        nd_eb = audit["net_debt_ebitda"]
        if nd_eb is not None:
            nd_col = GREEN if nd_eb <= 2.0 else (YELLOW if nd_eb <= 3.5 else RED)
            print(f"  • Net Debt / EBITDA:       {nd_col}{nd_eb:.2f}x{RESET}")

        print(f"  • Altman Z-Score:          {audit['altman_z']:.2f}")

        print(f"\n{CYAN}--- GROWTH & COMPOUNDING TRACK RECORD ---{RESET}")
        st_col = GREEN if audit["streak_years"] >= 10 else (YELLOW if audit["streak_years"] >= 5 else RED)
        print(f"  • Consecutive Growth:      {st_col}{audit['streak_years']} Years{RESET} uninterrupted dividend hikes")
        print(f"  • 1-Year Dividend Growth:  {audit['cagr_1y_pct']:+.2f}%")
        print(f"  • 3-Year Dividend CAGR:    {audit['cagr_3y_pct']:+.2f}%")
        print(f"  • 5-Year Dividend CAGR:    {audit['cagr_5y_pct']:+.2f}%")

        ch_col = GREEN if audit["chowder_number"] >= 10.0 else YELLOW
        print(f"  • Chowder Number:          {ch_col}{audit['chowder_number']:.2f}%{RESET} (Yield + 5Y CAGR)")

        if audit["cut_in_last_5y"]:
            print(f"\n  {RED}{BOLD}⚠ CRITICAL ALERT: Dividend cut or suspension detected in the past 5 years!{RESET}")

        if audit["warnings"]:
            print(f"\n{YELLOW}Audit Flags:{RESET}")
            for w in audit["warnings"]:
                print(f"  • {w}")

        print(f"\n{BOLD}Portfolio Eligibility:{RESET} {'✔ PASSED (Eligible for income allocation)' if audit['passed_gates'] else '✖ DISQUALIFIED (High risk or dividend trap)'}\n")


def main():
    parser = argparse.ArgumentParser(description="Dividend Reality Auditor")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. JNJ, PG, O, MO, INTC)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    auditor = DividendRealityAuditor(args.ticker)
    res = auditor.audit()

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        auditor.print_report(res)


def audit_dividend_stock(ticker: str) -> dict:
    """Convenience helper function to audit a dividend stock."""
    auditor = DividendRealityAuditor(ticker)
    return auditor.audit()


if __name__ == "__main__":
    main()
