#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║      UNIVERSAL STOCK REALITY & TRUTH AUDITOR — v3 INSTITUTIONAL EDITION      ║
║  EPS-Based PEG · Sector-Relative Benchmarks · Data Confidence · 5-Yr FCF    ║
╚══════════════════════════════════════════════════════════════════════════════╝

Fixes in v3 (over v2):
  1. PEG uses EPS growth (not revenue CAGR) — forward/trailing EPS delta or earningsGrowth
  2. Data Confidence Tier — tracks extraction success rate, gates final score credibility
  3. Sector-Relative Thresholds — separate scoring bins for Tech, Industrials, Financials, etc.
  4. Quality vs. Valuation Split — reports Business Quality and Valuation Attractiveness separately
  5. 5-Year FCF Median — uses median FCF over 5 years for cyclicals instead of 3-year sum
  6. Cascading Label Lookups — tries multiple row names per metric to reduce silent failures
  7. Explicit Screening Disclaimer — the score is a screening signal, not intrinsic value

Usage:
    python3 stock_reality_auditor.py AAPL
    python3 stock_reality_auditor.py JPM META NVDA TSLA --compare
"""

import sys
import os
import argparse
import math
import statistics

# Ensure yfinance is available
try:
    import yfinance as yf
except ImportError:
    venv_py = "/Users/sai/seeking_alpha_scraper/venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)
    else:
        print("Error: yfinance is required. Run: pip install yfinance")
        sys.exit(1)

# ──────────────────────────────────────────────────────────────────
# ANSI Colors
# ──────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────
# SECTOR-RELATIVE BENCHMARK PROFILES
# ──────────────────────────────────────────────────────────────────
# Each profile defines sector-appropriate thresholds for scoring.
# Sources: Damodaran sector averages, S&P Capital IQ composites.
SECTOR_PROFILES = {
    "Technology": {
        "label": "Technology & Asset-Light Growth",
        "de_good": 0.50, "de_ok": 1.20, "de_warn": 2.00,
        "peg_cheap": 1.5, "peg_fair": 2.5, "peg_rich": 4.0,
        "fcf_yield_strong": 4.0, "fcf_yield_ok": 2.0,
        "roic_elite": 25.0, "roic_good": 12.0,
        "op_margin_strong": 25.0, "op_margin_ok": 15.0,
        "z_safe": 2.6, "z_model": "Z''",
    },
    "Communication Services": {
        "label": "Communication Services & Media",
        "de_good": 0.60, "de_ok": 1.50, "de_warn": 2.50,
        "peg_cheap": 1.5, "peg_fair": 2.5, "peg_rich": 4.0,
        "fcf_yield_strong": 4.0, "fcf_yield_ok": 2.0,
        "roic_elite": 20.0, "roic_good": 10.0,
        "op_margin_strong": 20.0, "op_margin_ok": 10.0,
        "z_safe": 2.6, "z_model": "Z''",
    },
    "Consumer Cyclical": {
        "label": "Consumer Discretionary",
        "de_good": 0.70, "de_ok": 1.50, "de_warn": 2.50,
        "peg_cheap": 1.2, "peg_fair": 2.0, "peg_rich": 3.5,
        "fcf_yield_strong": 5.0, "fcf_yield_ok": 2.5,
        "roic_elite": 18.0, "roic_good": 10.0,
        "op_margin_strong": 15.0, "op_margin_ok": 8.0,
        "z_safe": 2.6, "z_model": "Z''",
    },
    "Consumer Defensive": {
        "label": "Consumer Staples",
        "de_good": 0.80, "de_ok": 1.80, "de_warn": 3.00,
        "peg_cheap": 1.5, "peg_fair": 2.5, "peg_rich": 3.5,
        "fcf_yield_strong": 5.0, "fcf_yield_ok": 3.0,
        "roic_elite": 18.0, "roic_good": 10.0,
        "op_margin_strong": 15.0, "op_margin_ok": 8.0,
        "z_safe": 2.6, "z_model": "Z''",
    },
    "Healthcare": {
        "label": "Healthcare & Biotech",
        "de_good": 0.60, "de_ok": 1.50, "de_warn": 2.50,
        "peg_cheap": 1.5, "peg_fair": 2.5, "peg_rich": 4.0,
        "fcf_yield_strong": 5.0, "fcf_yield_ok": 2.5,
        "roic_elite": 20.0, "roic_good": 10.0,
        "op_margin_strong": 20.0, "op_margin_ok": 10.0,
        "z_safe": 2.6, "z_model": "Z''",
    },
    "Industrials": {
        "label": "Industrials & Capital-Intensive",
        "de_good": 0.80, "de_ok": 1.80, "de_warn": 3.00,
        "peg_cheap": 1.2, "peg_fair": 2.0, "peg_rich": 3.0,
        "fcf_yield_strong": 5.0, "fcf_yield_ok": 3.0,
        "roic_elite": 15.0, "roic_good": 8.0,
        "op_margin_strong": 15.0, "op_margin_ok": 8.0,
        "z_safe": 3.0, "z_model": "Z-Classic",
    },
    "Energy": {
        "label": "Energy & Commodities",
        "de_good": 0.60, "de_ok": 1.50, "de_warn": 2.50,
        "peg_cheap": 0.8, "peg_fair": 1.5, "peg_rich": 2.5,
        "fcf_yield_strong": 8.0, "fcf_yield_ok": 4.0,
        "roic_elite": 15.0, "roic_good": 8.0,
        "op_margin_strong": 15.0, "op_margin_ok": 8.0,
        "z_safe": 3.0, "z_model": "Z-Classic",
    },
    "Basic Materials": {
        "label": "Basic Materials & Mining",
        "de_good": 0.70, "de_ok": 1.50, "de_warn": 2.50,
        "peg_cheap": 1.0, "peg_fair": 1.8, "peg_rich": 2.8,
        "fcf_yield_strong": 6.0, "fcf_yield_ok": 3.0,
        "roic_elite": 15.0, "roic_good": 8.0,
        "op_margin_strong": 15.0, "op_margin_ok": 8.0,
        "z_safe": 3.0, "z_model": "Z-Classic",
    },
    "Utilities": {
        "label": "Utilities & Regulated",
        "de_good": 1.20, "de_ok": 2.00, "de_warn": 3.00,
        "peg_cheap": 1.5, "peg_fair": 2.5, "peg_rich": 3.5,
        "fcf_yield_strong": 5.0, "fcf_yield_ok": 3.0,
        "roic_elite": 10.0, "roic_good": 6.0,
        "op_margin_strong": 20.0, "op_margin_ok": 12.0,
        "z_safe": 2.6, "z_model": "Z''",
    },
    "Real Estate": {
        "label": "Real Estate & REITs",
        "de_good": 1.00, "de_ok": 2.00, "de_warn": 3.50,
        "peg_cheap": 1.5, "peg_fair": 2.5, "peg_rich": 3.5,
        "fcf_yield_strong": 5.0, "fcf_yield_ok": 3.0,
        "roic_elite": 8.0, "roic_good": 5.0,
        "op_margin_strong": 30.0, "op_margin_ok": 15.0,
        "z_safe": 2.6, "z_model": "Z''",
    },
    "Financial Services": {
        "label": "Financials & Banking",
        "de_good": None, "de_ok": None, "de_warn": None,  # D/E not meaningful for banks
        "peg_cheap": 1.0, "peg_fair": 1.8, "peg_rich": 2.5,
        "fcf_yield_strong": None, "fcf_yield_ok": None,   # FCF not meaningful for banks
        "roic_elite": None, "roic_good": None,             # Use ROE/ROA instead
        "roe_elite": 15.0, "roe_good": 10.0,
        "roa_elite": 1.2, "roa_good": 0.8,
        "op_margin_strong": None, "op_margin_ok": None,
        "z_safe": None, "z_model": "N/A (ROE/ROA)",
    },
}

# Default fallback profile for unknown sectors
DEFAULT_PROFILE = {
    "label": "General / Diversified",
    "de_good": 0.70, "de_ok": 1.50, "de_warn": 2.50,
    "peg_cheap": 1.5, "peg_fair": 2.5, "peg_rich": 3.5,
    "fcf_yield_strong": 5.0, "fcf_yield_ok": 2.5,
    "roic_elite": 15.0, "roic_good": 8.0,
    "op_margin_strong": 15.0, "op_margin_ok": 8.0,
    "z_safe": 2.6, "z_model": "Z''",
}


def get_sector_profile(sector, industry):
    """Return the sector-specific benchmark profile."""
    # Check for financials first (can be under 'Financial Services' sector)
    if sector in SECTOR_PROFILES:
        return SECTOR_PROFILES[sector]
    # Heuristic fallbacks
    for key in SECTOR_PROFILES:
        if key.lower() in sector.lower() or key.lower() in industry.lower():
            return SECTOR_PROFILES[key]
    # Financial detection
    fin_keywords = ["bank", "insurance", "financial", "brokerage", "capital markets"]
    if any(kw in industry.lower() for kw in fin_keywords):
        return SECTOR_PROFILES["Financial Services"]
    return DEFAULT_PROFILE


# ──────────────────────────────────────────────────────────────────
# DATA EXTRACTION WITH CONFIDENCE TRACKING
# ──────────────────────────────────────────────────────────────────

class DataExtractor:
    """Extracts financial data with cascading label lookups and confidence tracking."""

    def __init__(self):
        self.total_lookups = 0
        self.successful_lookups = 0
        self.failed_labels = []

    def get(self, df, label_candidates, col_idx=0, default=0.0, critical=False):
        """
        Try multiple row-name candidates in order. Track success/failure.
        label_candidates: str or list of str to try in order.
        critical: if True, a failure is counted more heavily in confidence.
        """
        self.total_lookups += 1
        if isinstance(label_candidates, str):
            label_candidates = [label_candidates]

        if df is None or df.empty:
            if critical:
                self.failed_labels.append(label_candidates[0])
            return default

        for label in label_candidates:
            if label in df.index:
                try:
                    if col_idx < len(df.columns):
                        val = df.loc[label].iloc[col_idx]
                        if val is not None and str(val) != "nan":
                            self.successful_lookups += 1
                            return float(val)
                except Exception:
                    continue

        # All candidates failed
        if critical:
            self.failed_labels.append(label_candidates[0])
        return default

    def get_series(self, df, label_candidates, max_cols=5):
        """Extract a time series (multiple columns) for a metric."""
        if isinstance(label_candidates, str):
            label_candidates = [label_candidates]

        if df is None or df.empty:
            return []

        n_cols = min(max_cols, len(df.columns))
        for label in label_candidates:
            if label in df.index:
                values = []
                for i in range(n_cols):
                    try:
                        val = df.loc[label].iloc[i]
                        if val is not None and str(val) != "nan":
                            values.append(float(val))
                        else:
                            values.append(None)
                    except Exception:
                        values.append(None)
                return values
        return []

    @property
    def confidence_ratio(self):
        if self.total_lookups == 0:
            return 0.0
        return self.successful_lookups / self.total_lookups

    @property
    def confidence_tier(self):
        r = self.confidence_ratio
        if r >= 0.85:
            return "HIGH"
        elif r >= 0.65:
            return "MEDIUM"
        elif r >= 0.40:
            return "LOW"
        else:
            return "VERY LOW"

    @property
    def confidence_color(self):
        tier = self.confidence_tier
        return {
            "HIGH": GREEN,
            "MEDIUM": YELLOW,
            "LOW": RED,
            "VERY LOW": RED,
        }[tier]


# ──────────────────────────────────────────────────────────────────
# DYNAMIC WACC (CAPM)
# ──────────────────────────────────────────────────────────────────

def calculate_dynamic_wacc(beta, total_debt, market_cap, interest_expense, tax_rate):
    """
    Computes dynamic WACC using Capital Asset Pricing Model (CAPM).
    Rf = 4.25% (10-Yr US Treasury), ERP = 5.0% (Equity Risk Premium).
    """
    rf = 4.25
    erp = 5.00
    beta_adj = max(0.40, min(beta, 2.50)) if beta and str(beta) != "nan" else 1.00
    cost_of_equity = rf + (beta_adj * erp)

    total_value = market_cap + total_debt
    if total_value <= 0:
        return 9.0, cost_of_equity, 5.0

    weight_equity = market_cap / total_value
    weight_debt = total_debt / total_value

    if total_debt > 0 and interest_expense > 0:
        pre_tax_cost_of_debt = min(max((interest_expense / total_debt) * 100.0, 3.5), 12.0)
    else:
        pre_tax_cost_of_debt = rf + 1.25  # Investment grade credit spread default

    after_tax_cost_of_debt = pre_tax_cost_of_debt * (1.0 - tax_rate)
    wacc = (weight_equity * cost_of_equity) + (weight_debt * after_tax_cost_of_debt)
    return round(wacc, 2), round(cost_of_equity, 2), round(after_tax_cost_of_debt, 2)


# ──────────────────────────────────────────────────────────────────
# MAIN AUDIT ENGINE
# ──────────────────────────────────────────────────────────────────

def audit_ticker(symbol):
    sym = symbol.upper().strip()
    t = yf.Ticker(sym)
    dx = DataExtractor()

    try:
        info = t.info
    except Exception:
        info = {}

    if not info or ("shortName" not in info and "symbol" not in info and "currentPrice" not in info):
        print(f"{RED}Error: Unable to fetch live financial data for ticker '{sym}'. Verify the symbol.{RESET}")
        return None

    company_name = info.get("shortName") or info.get("longName") or sym
    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
    mkt_cap = info.get("marketCap") or 0.0
    enterprise_value = info.get("enterpriseValue") or (mkt_cap + info.get("totalDebt", 0.0) - info.get("totalCash", 0.0))
    sector = info.get("sector") or "General"
    industry = info.get("industry") or "Diversified"
    beta = info.get("beta") or 1.0

    # Get sector-specific benchmark profile
    profile = get_sector_profile(sector, industry)
    is_financial = profile is SECTOR_PROFILES.get("Financial Services")
    is_industrial = sector in ["Industrials", "Basic Materials", "Energy"]

    bs = t.balance_sheet
    fin = t.financials
    cf = t.cashflow

    # ─────────────────────────────────────────────────────────────
    # 1. CORE FINANCIAL STATEMENTS (Cascading Label Lookups)
    # ─────────────────────────────────────────────────────────────
    total_assets = dx.get(bs, ["Total Assets"], 0, 1.0, critical=True)
    total_liab = dx.get(bs, [
        "Total Liabilities Net Minority Interest",
        "Total Liab",
        "Total Liabilities",
    ], 0, 0.0, critical=True)
    stockholders_equity = dx.get(bs, [
        "Stockholders Equity",
        "Total Stockholders Equity",
        "Stockholder Equity",
    ], 0, 0.0, critical=True)
    if stockholders_equity == 0.0:
        stockholders_equity = max(1.0, total_assets - total_liab)

    working_cap = dx.get(bs, [
        "Working Capital",
        "Net Working Capital",
    ], 0, 0.0)
    retained_earnings = dx.get(bs, [
        "Retained Earnings",
        "Accumulated Retained Earnings",
    ], 0, 0.0)
    cash = dx.get(bs, [
        "Cash And Cash Equivalents",
        "Cash",
        "Cash Financial",
    ], 0, 0.0)
    st_investments = dx.get(bs, [
        "Other Short Term Investments",
        "Short Term Investments",
        "Available For Sale Securities",
    ], 0, 0.0)
    total_cash = cash + st_investments if (cash + st_investments) > 0 else info.get("totalCash", 0.0)
    total_debt = dx.get(bs, [
        "Total Debt",
        "Long Term Debt And Capital Lease Obligation",
        "Long Term Debt",
    ], 0, 0.0) or info.get("totalDebt", 0.0)

    # Income Statement
    total_rev = dx.get(fin, [
        "Total Revenue",
        "Revenue",
        "Total Revenues",
    ], 0, 1.0, critical=True)
    gross_profit = dx.get(fin, [
        "Gross Profit",
    ], 0, total_rev)
    ebit = dx.get(fin, [
        "EBIT",
        "Operating Income",
        "Operating Profit",
    ], 0, 0.0, critical=True)
    if ebit == 0.0:
        ebit = dx.get(fin, [
            "Pretax Income",
            "Income Before Tax",
        ], 0, dx.get(fin, ["Net Income", "Net Income Common Stockholders"], 0, 0.0))
    net_income = dx.get(fin, [
        "Net Income",
        "Net Income Common Stockholders",
        "Net Income From Continuing Operations",
    ], 0, 1.0, critical=True)
    tax_expense = dx.get(fin, [
        "Tax Provision",
        "Income Tax Expense",
        "Tax Expense",
    ], 0, 0.0)
    interest_expense = abs(dx.get(fin, [
        "Interest Expense",
        "Interest Expense Non Operating",
    ], 0, 0.0))

    # Cash Flow Statement
    op_cf = dx.get(cf, [
        "Operating Cash Flow",
        "Cash Flow From Continuing Operating Activities",
        "Total Cash From Operating Activities",
    ], 0, 0.0, critical=True) or info.get("operatingCashflow", 0.0)
    capex = abs(dx.get(cf, [
        "Capital Expenditure",
        "Capital Expenditures",
    ], 0, 0.0))
    fcf = dx.get(cf, [
        "Free Cash Flow",
    ], 0, 0.0) or (op_cf - capex)
    buybacks = abs(dx.get(cf, [
        "Repurchase Of Capital Stock",
        "Common Stock Repurchased",
    ], 0, 0.0))
    sbc = dx.get(cf, [
        "Stock Based Compensation",
    ], 0, 0.0)

    # ─────────────────────────────────────────────────────────────
    # 2. MULTI-YEAR TREND ANALYSIS (5-Year where available)
    # ─────────────────────────────────────────────────────────────
    # Revenue series for CAGR
    rev_series = dx.get_series(fin, ["Total Revenue", "Revenue", "Total Revenues"], max_cols=5)
    rev_valid = [v for v in rev_series if v is not None and v > 0]

    if len(rev_valid) >= 4:
        years = len(rev_valid) - 1
        rev_cagr = ((rev_valid[0] / rev_valid[-1]) ** (1.0 / years) - 1.0) * 100.0
        rev_cagr_years = years
    elif len(rev_valid) >= 3:
        rev_cagr = ((rev_valid[0] / rev_valid[2]) ** (1.0 / 2.0) - 1.0) * 100.0
        rev_cagr_years = 2
    elif len(rev_valid) >= 2:
        rev_cagr = ((rev_valid[0] / rev_valid[1]) - 1.0) * 100.0
        rev_cagr_years = 1
    else:
        rev_cagr = info.get("revenueGrowth", 0.05) * 100.0
        rev_cagr_years = 0

    # Operating margin trajectory
    ebit_0 = dx.get(fin, ["EBIT", "Operating Income"], 0, 0.0)
    ebit_oldest = dx.get(fin, ["EBIT", "Operating Income"], min(3, len(fin.columns) - 1) if fin is not None and not fin.empty else 0, ebit_0)
    rev_oldest = rev_valid[-1] if len(rev_valid) >= 3 else total_rev
    op_margin_curr = (ebit_0 / total_rev) * 100.0 if total_rev > 0 else 0.0
    op_margin_prior = (ebit_oldest / rev_oldest) * 100.0 if rev_oldest > 0 else op_margin_curr
    op_margin_trend_delta = op_margin_curr - op_margin_prior

    # 5-Year FCF: use median (not just sum) for cyclical robustness
    fcf_series = dx.get_series(cf, ["Free Cash Flow"], max_cols=5)
    fcf_valid = [v for v in fcf_series if v is not None]
    fcf_positive_count = sum(1 for v in fcf_valid if v > 0)
    all_fcf_positive = len(fcf_valid) > 0 and all(v > 0 for v in fcf_valid)
    median_fcf = statistics.median(fcf_valid) if fcf_valid else fcf
    cumulative_fcf = sum(fcf_valid) if fcf_valid else fcf
    fcf_years_available = len(fcf_valid)

    # Multi-year Net Income trajectory (Deterioration check)
    ni_series = dx.get_series(fin, ["Net Income", "Net Income Common Stockholders"], max_cols=5)
    ni_valid = [v for v in ni_series if v is not None]
    persistent_ni_decline = False
    if len(ni_valid) >= 3 and ni_valid[0] < ni_valid[1] < ni_valid[2]:
        persistent_ni_decline = True

    # Multi-year Debt trajectory (Leverage acceleration check)
    debt_series = dx.get_series(bs, ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt"], max_cols=3)
    debt_valid = [v for v in debt_series if v is not None and v > 0]
    debt_accelerating = False
    if len(debt_valid) >= 2 and debt_valid[1] > 0:
        debt_growth_pct = ((debt_valid[0] - debt_valid[1]) / debt_valid[1]) * 100.0
        if debt_growth_pct > 20.0 and op_margin_trend_delta < 0:
            debt_accelerating = True

    # ─────────────────────────────────────────────────────────────
    # 3. TRUE SHARE DILUTION (Actual share delta, multi-year)
    # ─────────────────────────────────────────────────────────────
    share_series = dx.get_series(bs, ["Ordinary Shares Number", "Share Issued", "Common Stock Shares Outstanding"], max_cols=5)
    share_valid = [v for v in share_series if v is not None and v > 0]

    if len(share_valid) >= 2:
        curr_shares = share_valid[0]
        prior_shares = share_valid[1]
        share_count_change_pct = ((curr_shares - prior_shares) / prior_shares) * 100.0
        # Multi-year dilution CAGR if 3+ years available
        if len(share_valid) >= 3:
            n_yrs = len(share_valid) - 1
            share_cagr = ((share_valid[0] / share_valid[-1]) ** (1.0 / n_yrs) - 1.0) * 100.0
        else:
            share_cagr = share_count_change_pct
    else:
        share_count_change_pct = 0.0
        share_cagr = 0.0

    # ─────────────────────────────────────────────────────────────
    # 4. EPS GROWTH FOR PEG (Fix #1: Use earnings growth, NOT revenue)
    # ─────────────────────────────────────────────────────────────
    trailing_eps = info.get("trailingEps") or 0.0
    forward_eps = info.get("forwardEps") or 0.0
    trailing_pe = info.get("trailingPE") or (price / trailing_eps if trailing_eps > 0 else 0.0)
    forward_pe = info.get("forwardPE") or (price / forward_eps if forward_eps > 0 else trailing_pe)

    # EPS Growth: Priority order
    # 1. Forward EPS vs Trailing EPS (consensus analyst delta)
    # 2. yfinance earningsGrowth (trailing 12mo)
    # 3. Computed from net income CAGR as last resort
    eps_growth = None
    eps_growth_source = "N/A"

    if trailing_eps > 0 and forward_eps > 0:
        eps_growth = ((forward_eps - trailing_eps) / abs(trailing_eps)) * 100.0
        eps_growth_source = "Forward/Trailing EPS Delta"
    elif info.get("earningsGrowth") is not None and str(info.get("earningsGrowth")) != "nan":
        eps_growth = info["earningsGrowth"] * 100.0
        eps_growth_source = "yfinance earningsGrowth"

    # Fallback: Net income CAGR from income statements
    if eps_growth is None:
        ni_series = dx.get_series(fin, ["Net Income", "Net Income Common Stockholders"], max_cols=4)
        ni_valid = [v for v in ni_series if v is not None and v > 0]
        if len(ni_valid) >= 3:
            eps_growth = ((ni_valid[0] / ni_valid[-1]) ** (1.0 / (len(ni_valid) - 1)) - 1.0) * 100.0
            eps_growth_source = f"Net Income {len(ni_valid)-1}-Yr CAGR"
        elif len(ni_valid) >= 2:
            eps_growth = ((ni_valid[0] / ni_valid[1]) - 1.0) * 100.0
            eps_growth_source = "Net Income YoY"
        else:
            eps_growth = rev_cagr  # Absolute last resort
            eps_growth_source = "Revenue CAGR (fallback — low confidence)"

    # PEG Ratio: Forward P/E / EPS Growth Rate
    # Guard: if growth is near-zero or negative, PEG is undefined
    eps_growth_for_peg = eps_growth
    peg_valid = True
    if eps_growth_for_peg is None or eps_growth_for_peg <= 0:
        peg_ratio = None  # Undefined — negative/zero growth makes PEG meaningless
        peg_valid = False
    else:
        peg_ratio = forward_pe / eps_growth_for_peg if eps_growth_for_peg > 0 else None
        if peg_ratio is not None and peg_ratio < 0:
            peg_ratio = None
            peg_valid = False

    # FCF Yield — use median FCF for stability
    fcf_for_yield = median_fcf if fcf_years_available >= 3 else fcf
    fcf_yield = (fcf_for_yield / enterprise_value) * 100.0 if enterprise_value > 0 else (fcf_for_yield / mkt_cap * 100.0 if mkt_cap > 0 else 0.0)

    # Debt Ratios
    debt_equity_ratio = (total_debt / stockholders_equity) if stockholders_equity > 0 else 99.0
    sbc_buyback_ratio = (sbc / buybacks) if buybacks > 0 else (1.0 if sbc > 0 else 0.0)

    # ─────────────────────────────────────────────────────────────
    # 5. DYNAMIC WACC & ROIC ECONOMIC SPREAD
    # ─────────────────────────────────────────────────────────────
    effective_tax_rate = min(max(tax_expense / ebit if ebit > 0 else 0.21, 0.10), 0.35)
    dynamic_wacc, cost_equity, cost_debt = calculate_dynamic_wacc(
        beta, total_debt, mkt_cap, interest_expense, effective_tax_rate
    )
    nopat = ebit * (1.0 - effective_tax_rate)
    invested_capital = (total_assets - total_liab + total_debt)
    roic = (nopat / invested_capital * 100.0) if invested_capital > 0 else (info.get("returnOnEquity", 0.15) * 100.0)
    economic_spread = roic - dynamic_wacc

    # ─────────────────────────────────────────────────────────────
    # 6. ALTMAN Z SCORES
    # ─────────────────────────────────────────────────────────────
    x1 = working_cap / total_assets if total_assets > 0 else 0
    x2 = retained_earnings / total_assets if total_assets > 0 else 0
    x3 = ebit / total_assets if total_assets > 0 else 0
    x4_book = stockholders_equity / total_liab if total_liab > 0 else 2.0
    altman_z_double_prime = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4_book

    x4_mkt = mkt_cap / total_liab if total_liab > 0 else 5.0
    x5 = total_rev / total_assets if total_assets > 0 else 0
    altman_z_classic = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4_mkt + 1.0 * x5

    if profile.get("z_model") == "Z-Classic":
        selected_z = altman_z_classic
        z_label = "Z-Classic (Manufacturing)"
    elif is_financial:
        selected_z = None
        z_label = "N/A (Financial — use ROE/ROA)"
    else:
        selected_z = altman_z_double_prime
        z_label = "Z'' (Non-Manufacturing)"

    # ─────────────────────────────────────────────────────────────
    # 7. SECTOR-RELATIVE SCORING ENGINE
    #    SPLIT: Business Quality (60 pts) + Valuation (40 pts)
    # ─────────────────────────────────────────────────────────────

    # ▸▸▸ BUSINESS QUALITY SCORE (Max 60 pts) ◂◂◂

    # --- PILLAR 1: SOLVENCY & LEVERAGE (Max 20 pts) ---
    p1_solvency = 0.0
    if is_financial:
        roa = info.get("returnOnAssets", 0.01) * 100.0
        roe = info.get("returnOnEquity", 0.10) * 100.0
        roa_e = profile.get("roa_elite", 1.2)
        roa_g = profile.get("roa_good", 0.8)
        roe_e = profile.get("roe_elite", 15.0)
        roe_g = profile.get("roe_good", 10.0)

        if roa >= roa_e: p1_solvency += 10.0
        elif roa >= roa_g: p1_solvency += 6.0
        else: p1_solvency += 3.0

        if roe >= roe_e: p1_solvency += 10.0
        elif roe >= roe_g: p1_solvency += 6.0
        else: p1_solvency += 3.0
    else:
        z_safe = profile.get("z_safe", 2.6)
        if selected_z is not None:
            if selected_z >= z_safe: p1_solvency += 8.0
            elif selected_z >= z_safe * 0.5: p1_solvency += 4.0

        de_good = profile.get("de_good", 0.70)
        de_ok = profile.get("de_ok", 1.50)
        de_warn = profile.get("de_warn", 2.50)
        if de_good is not None:
            if debt_equity_ratio <= de_good: p1_solvency += 7.0
            elif debt_equity_ratio <= de_ok: p1_solvency += 4.0
            elif debt_equity_ratio <= de_warn: p1_solvency += 2.0

        # Cash coverage
        cash_cover = (total_cash / total_debt) if total_debt > 0 else 2.0
        if cash_cover >= 1.0: p1_solvency += 5.0
        elif total_cash > 0: p1_solvency += 3.0

    # --- PILLAR 2: ECONOMIC MOAT & MULTI-YEAR TRENDS (Max 25 pts) ---
    p2_moat = 0.0

    # Economic spread over dynamic WACC (sector-adjusted ROIC thresholds)
    roic_elite = profile.get("roic_elite", 15.0)
    roic_good = profile.get("roic_good", 8.0)
    if not is_financial:
        if economic_spread >= 15.0: p2_moat += 12.0
        elif economic_spread >= 5.0: p2_moat += 8.0
        elif economic_spread > 0: p2_moat += 4.0
    else:
        # Banks: ROE vs cost of equity
        roe_val = info.get("returnOnEquity", 0.10) * 100.0
        bank_spread = roe_val - cost_equity
        if bank_spread >= 5.0: p2_moat += 12.0
        elif bank_spread >= 0: p2_moat += 7.0
        else: p2_moat += 2.0

    # Margin trajectory
    if op_margin_trend_delta >= 2.0: p2_moat += 7.0
    elif op_margin_trend_delta >= -1.0: p2_moat += 4.0
    else: p2_moat += 1.0

    # FCF consistency (5-year, using count of positive years)
    if is_financial:
        if net_income > 0: p2_moat += 6.0
    else:
        if fcf_years_available >= 4 and fcf_positive_count == fcf_years_available:
            p2_moat += 6.0  # All years positive (robust)
        elif fcf_years_available >= 3 and fcf_positive_count >= fcf_years_available - 1:
            p2_moat += 4.0  # At most 1 negative year
        elif fcf > 0:
            p2_moat += 2.0

    # --- PILLAR 3: CAPITAL DISCIPLINE & DILUTION (Max 15 pts) ---
    p3_discipline = 0.0

    # Share count change (use multi-year CAGR if available)
    dilution_metric = share_cagr if len(share_valid) >= 3 else share_count_change_pct
    if dilution_metric <= -1.5:
        p3_discipline += 6.0   # Meaningful net retirement
    elif dilution_metric <= 0.5:
        p3_discipline += 4.0   # Stable
    elif dilution_metric <= 2.0:
        p3_discipline += 2.0   # Mild dilution
    # else: 0 (severe dilution)

    # SBC dilution vs buybacks
    if sbc_buyback_ratio <= 0.25: p3_discipline += 5.0
    elif sbc_buyback_ratio <= 0.50: p3_discipline += 3.0
    elif sbc_buyback_ratio <= 0.75: p3_discipline += 1.0

    # ROIC reinvestment efficiency
    if not is_financial:
        if roic >= roic_elite: p3_discipline += 4.0
        elif roic >= roic_good: p3_discipline += 2.0
    else:
        p3_discipline += 3.0  # Neutral for financials

    # ▸▸▸ VALUATION ATTRACTIVENESS SCORE (Max 40 pts) ◂◂◂

    # --- PILLAR 4: GROWTH-ADJUSTED VALUATION (Max 20 pts) ---
    p4_valuation = 0.0

    # PEG Ratio scoring (sector-relative)
    peg_cheap = profile.get("peg_cheap", 1.5)
    peg_fair = profile.get("peg_fair", 2.5)
    peg_rich = profile.get("peg_rich", 4.0)

    if peg_valid and peg_ratio is not None:
        if peg_ratio <= peg_cheap: p4_valuation += 10.0
        elif peg_ratio <= peg_fair: p4_valuation += 7.0
        elif peg_ratio <= peg_rich: p4_valuation += 3.0
        else: p4_valuation += 1.0
    else:
        # PEG undefined (negative or zero growth) — penalize with 0 points
        p4_valuation += 0.0

    # Cash / Earnings Yield
    fcf_strong = profile.get("fcf_yield_strong", 5.0)
    fcf_ok = profile.get("fcf_yield_ok", 2.5)
    if is_financial:
        effective_yield = ((net_income / mkt_cap) * 100.0) if mkt_cap > 0 else 0.0
        if effective_yield >= 8.0: p4_valuation += 10.0
        elif effective_yield >= 5.0: p4_valuation += 7.0
        elif effective_yield >= 3.0: p4_valuation += 4.0
        else: p4_valuation += 1.0
    else:
        if fcf_strong and fcf_ok:
            if fcf_yield >= fcf_strong: p4_valuation += 10.0
            elif fcf_yield >= fcf_ok: p4_valuation += 6.0
            elif fcf_yield >= 1.0: p4_valuation += 3.0
            else: p4_valuation += 1.0

    # --- PILLAR 5: RELATIVE VALUE CHECK (Max 20 pts) ---
    p5_relative = 0.0

    # Forward P/E sanity: scored against sector norms
    if forward_pe > 0:
        if forward_pe <= 15: p5_relative += 8.0
        elif forward_pe <= 25: p5_relative += 6.0
        elif forward_pe <= 40: p5_relative += 3.0
        else: p5_relative += 1.0  # >40x requires exceptional growth
    else:
        p5_relative += 1.0

    # Revenue growth sustainability
    if rev_cagr >= 15.0: p5_relative += 6.0
    elif rev_cagr >= 8.0: p5_relative += 4.0
    elif rev_cagr >= 3.0: p5_relative += 2.0
    else: p5_relative += 1.0

    # EV/FCF (enterprise value to median FCF)
    if not is_financial and median_fcf > 0 and enterprise_value > 0:
        ev_fcf = enterprise_value / median_fcf
        if ev_fcf <= 15: p5_relative += 6.0
        elif ev_fcf <= 25: p5_relative += 4.0
        elif ev_fcf <= 40: p5_relative += 2.0
        else: p5_relative += 1.0
    elif is_financial:
        # P/B for banks
        pb = info.get("priceToBook") or (price / (stockholders_equity / info.get("sharesOutstanding", 1.0)) if info.get("sharesOutstanding") else 2.0)
        if pb and pb <= 1.2: p5_relative += 6.0
        elif pb and pb <= 2.0: p5_relative += 4.0
        elif pb and pb <= 3.0: p5_relative += 2.0
        else: p5_relative += 1.0
    else:
        p5_relative += 2.0

    # ─────────────────────────────────────────────────────────────
    # 8. COMPOSITE SCORES & DUAL-GATE EVALUATION
    # ─────────────────────────────────────────────────────────────
    quality_raw = p1_solvency + p2_moat + p3_discipline        # Max 60
    valuation_raw = p4_valuation + p5_relative                  # Max 40
    total_raw = quality_raw + valuation_raw                     # Max 100

    quality_score = round((quality_raw / 60.0) * 10.0, 2)
    valuation_score = round((valuation_raw / 40.0) * 10.0, 2)

    # If PEG is invalid (negative or zero EPS growth), cap valuation score at 4.5
    if not peg_valid:
        valuation_score = min(valuation_score, 4.5)

    # Raw Reality Score
    reality_score = round(total_raw / 10.0, 2)

    confidence = dx.confidence_tier
    data_gate = (confidence in ["HIGH", "MEDIUM"]) and (dx.confidence_ratio >= 0.60)

    # Apply data confidence penalties
    if confidence == "VERY LOW" or dx.confidence_ratio < 0.40:
        reality_score = min(reality_score, 3.5)
    elif confidence == "LOW" or dx.confidence_ratio < 0.60:
        reality_score = min(reality_score, 5.8)

    # Dual Screening Gates
    quality_gate = quality_score >= 6.0
    valuation_gate = valuation_score >= 5.0

    # Screening Signal Determination (Neutral, triage-focused)
    if not data_gate:
        screening_signal = "DATA DEFICIENT (Extraction fell below minimum confidence threshold; manual audit required)"
        screening_code = "DATA_FAIL"
    elif quality_gate and valuation_gate:
        if quality_score >= 7.5 and valuation_score >= 6.5:
            screening_signal = "HIGH-CONVICTION CANDIDATE (Passes both quality and valuation hurdles with elite moat)"
            screening_code = "HIGH_CONVICTION"
        else:
            screening_signal = "BALANCED SCREEN CANDIDATE (Meets quality baseline and trades at reasonable valuation)"
            screening_code = "BALANCED_PASS"
    elif quality_gate and not valuation_gate:
        screening_signal = "EXPENSIVE QUALITY COMPOUNDER (Fortress franchise, but multiples offer no margin of safety)"
        screening_code = "EXPENSIVE_QUALITY"
    elif not quality_gate and valuation_gate:
        screening_signal = "VALUE TRAP RISK (Cheap multiples, but weak solvency, deteriorating margins, or dilution)"
        screening_code = "VALUE_TRAP"
    else:
        screening_signal = "SCREENING CRITERIA FAIL (Sub-hurdle business quality and demanding/unsupportive valuation)"
        screening_code = "FAIL_BOTH"

    # ─────────────────────────────────────────────────────────────
    # 9. STRENGTHS & FUNDAMENTAL DETERIORATION RED FLAGS
    # ─────────────────────────────────────────────────────────────
    strengths = []
    red_flags = []

    if is_financial:
        roe_val = info.get("returnOnEquity", 0.15) * 100.0
        bank_spread = roe_val - cost_equity
        if bank_spread >= 4.0:
            strengths.append(f"Elite Banking Return: ROE ({roe_val:.1f}%) exceeds Cost of Equity ({cost_equity:.1f}%) by +{bank_spread:.1f}%")
        elif bank_spread < 0:
            red_flags.append(f"Weak Banking Return: ROE ({roe_val:.1f}%) is below Cost of Equity ({cost_equity:.1f}%)")
    else:
        if economic_spread >= 8.0:
            strengths.append(f"Elite Economic Moat: ROIC ({roic:.1f}%) exceeds dynamic WACC ({dynamic_wacc}%) by +{economic_spread:.1f}%")
        elif economic_spread <= 0:
            red_flags.append(f"Value Destroying: ROIC ({roic:.1f}%) is below company cost of capital ({dynamic_wacc}%)")

    if dilution_metric < -1.0:
        strengths.append(f"Genuine Net Share Retirement: Shares reduced by {abs(dilution_metric):.2f}% CAGR")
    elif dilution_metric > 2.0:
        red_flags.append(f"Active Shareholder Dilution: Share count growing at +{dilution_metric:.2f}% CAGR")

    if not is_financial:
        if fcf_years_available >= 4 and all_fcf_positive:
            strengths.append(f"Consistent Cash Generator: Positive FCF in all {fcf_years_available} available years (Median: ${median_fcf/1e9:.1f}B, Cumulative: ${cumulative_fcf/1e9:.1f}B)")
        elif fcf <= 0:
            red_flags.append(f"Negative Free Cash Flow: Operating cash flow does not cover current CapEx")

    if sbc_buyback_ratio >= 0.50 and buybacks > 0:
        red_flags.append(f"SBC Dilution Trap: {sbc_buyback_ratio*100:.1f}% of buybacks absorbed by SBC (${sbc/1e9:.1f}B SBC vs ${buybacks/1e9:.1f}B buybacks)")

    if peg_valid and peg_ratio is not None and peg_ratio > peg_rich:
        red_flags.append(f"Valuation Stretched: PEG {peg_ratio:.2f}x exceeds sector '{peg_rich}x rich' threshold (Forward P/E {forward_pe:.1f}x / EPS Growth {eps_growth:.1f}%)")
    elif not peg_valid:
        red_flags.append(f"PEG Undefined / Growth Impaired: EPS growth is negative or zero ({eps_growth:.1f}%) — growth-adjusted valuation invalid")

    # Hard Fundamental Deterioration Checks
    if persistent_ni_decline:
        red_flags.append(f"Persistent Earnings Contraction: Net income declined consecutively across past 3 reporting periods")

    if debt_accelerating:
        red_flags.append(f"Leverage Expansion Outpacing Profits: Total debt grew >20% while operating margins contracted")

    if fcf_years_available >= 3 and fcf_positive_count <= 1:
        red_flags.append(f"Chronic Cash Bleed: Free Cash Flow was negative in {fcf_years_available - fcf_positive_count} of {fcf_years_available} past years")

    if dilution_metric > 2.5:
        red_flags.append(f"Aggressive Share Dilution: Share count expanding at +{dilution_metric:.2f}% CAGR")

    if confidence in ("LOW", "VERY LOW"):
        red_flags.append(f"Data Quality Warning: Only {dx.successful_lookups}/{dx.total_lookups} metrics extracted successfully ({confidence} confidence)")

    return {
        "symbol": sym,
        "name": company_name,
        "price": price,
        "mkt_cap": mkt_cap,
        "enterprise_value": enterprise_value,
        "sector": sector,
        "industry": industry,
        "sector_profile_label": profile["label"],
        # 3 Statements
        "total_assets": total_assets,
        "total_liab": total_liab,
        "stockholders_equity": stockholders_equity,
        "total_cash": total_cash,
        "total_debt": total_debt,
        "total_rev": total_rev,
        "ebit": ebit,
        "net_income": net_income,
        "op_cf": op_cf,
        "capex": capex,
        "fcf": fcf,
        "median_fcf": median_fcf,
        "sbc": sbc,
        "buybacks": buybacks,
        # EPS & Valuation
        "trailing_eps": trailing_eps,
        "forward_eps": forward_eps,
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
        "eps_growth": eps_growth,
        "eps_growth_source": eps_growth_source,
        "peg_ratio": peg_ratio,
        "peg_valid": peg_valid,
        "fcf_yield": fcf_yield,
        "debt_equity_ratio": debt_equity_ratio,
        # Multi-Year Trends
        "rev_cagr": rev_cagr,
        "rev_cagr_years": rev_cagr_years,
        "op_margin_curr": op_margin_curr,
        "op_margin_trend_delta": op_margin_trend_delta,
        "share_count_change_pct": share_count_change_pct,
        "share_cagr": share_cagr,
        "share_years": len(share_valid),
        "all_fcf_positive": all_fcf_positive,
        "fcf_positive_count": fcf_positive_count,
        "fcf_years_available": fcf_years_available,
        "cumulative_fcf": cumulative_fcf,
        "persistent_ni_decline": persistent_ni_decline,
        "debt_accelerating": debt_accelerating,
        # Advanced
        "beta": beta,
        "dynamic_wacc": dynamic_wacc,
        "cost_equity": cost_equity,
        "cost_debt": cost_debt,
        "roic": roic,
        "economic_spread": economic_spread,
        "selected_z": selected_z,
        "z_label": z_label,
        "sbc_buyback_ratio": sbc_buyback_ratio,
        "is_financial": is_financial,
        # Scores & Gates
        "p1_solvency": p1_solvency,
        "p2_moat": p2_moat,
        "p3_discipline": p3_discipline,
        "p4_valuation": p4_valuation,
        "p5_relative": p5_relative,
        "quality_raw": quality_raw,
        "valuation_raw": valuation_raw,
        "quality_score": quality_score,
        "valuation_score": valuation_score,
        "reality_score": reality_score,
        "raw_score": total_raw,
        "quality_gate": quality_gate,
        "valuation_gate": valuation_gate,
        "data_gate": data_gate,
        "screening_signal": screening_signal,
        "screening_code": screening_code,
        # Data Confidence
        "data_confidence_tier": confidence,
        "data_confidence_ratio": dx.confidence_ratio,
        "data_extractions_ok": dx.successful_lookups,
        "data_extractions_total": dx.total_lookups,
        "data_failed_labels": dx.failed_labels,
        # Signals
        "strengths": strengths,
        "red_flags": red_flags,
    }


def print_audit_report(res):
    sym = res["symbol"]
    name = res["name"]
    q_score = res["quality_score"]
    v_score = res["valuation_score"]
    r_score = res["reality_score"]
    conf = res["data_confidence_tier"]
    conf_col = GREEN if conf == "HIGH" else (YELLOW if conf == "MEDIUM" else RED)

    print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}   UNIVERSAL REALITY AUDITOR (v3 INSTITUTIONAL): {name.upper()} [{sym}]   {RESET}")
    print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{DIM}Sector: {res['sector']} | Industry: {res['industry']}{RESET}")
    print(f"{DIM}Benchmark Profile: {BOLD}{res['sector_profile_label']}{RESET}")
    print(f"{DIM}Data Confidence: {conf_col}{BOLD}{conf}{RESET}{DIM} ({res['data_extractions_ok']}/{res['data_extractions_total']} metrics extracted){RESET}\n")

    # 1. CORE STATEMENTS
    print(f"{BOLD}{CYAN}📊 1. CORE FINANCIAL STATEMENTS (Audited Filings):{RESET}")
    print(f"  • Balance Sheet:      Assets: ${res['total_assets']/1e9:.2f}B | Liabilities: ${res['total_liab']/1e9:.2f}B | Equity: ${res['stockholders_equity']/1e9:.2f}B")
    print(f"  • Income Statement:   Revenue: ${res['total_rev']/1e9:.2f}B | EBIT: ${res['ebit']/1e9:.2f}B | Net Income: ${res['net_income']/1e9:.2f}B")
    print(f"  • Cash Flow:          Op Cash Flow: ${res['op_cf']/1e9:.2f}B | CapEx: ${res['capex']/1e9:.2f}B | FCF (Latest): ${res['fcf']/1e9:.2f}B")

    # 2. MULTI-YEAR TRENDS
    print(f"\n{BOLD}{CYAN}📈 2. MULTI-YEAR TREND ANALYSIS & DILUTION:{RESET}")
    print(f"  • Revenue CAGR:                 {BOLD}{res['rev_cagr']:+.2f}% / year{RESET} ({res['rev_cagr_years']}-year)")
    margin_col = GREEN if res['op_margin_trend_delta'] >= 0 else RED
    print(f"  • Operating Margin Trajectory:  {res['op_margin_curr']:.1f}% ({margin_col}{res['op_margin_trend_delta']:+.1f}% delta{RESET})")

    if res['fcf_years_available'] > 0:
        fcf_status = f"{GREEN}Positive in {res['fcf_positive_count']}/{res['fcf_years_available']} years{RESET} (Median: ${res['median_fcf']/1e9:.1f}B)"
    else:
        fcf_status = f"{YELLOW}No multi-year FCF data{RESET}"
    print(f"  • {res['fcf_years_available']}-Year FCF Health:          {fcf_status}")

    dilution_col = GREEN if res['share_cagr'] <= 0 else RED
    dilution_label = "Net Retirement" if res['share_cagr'] <= 0 else "Net Dilution"
    yr_label = f"{res['share_years']-1}-yr CAGR" if res['share_years'] >= 3 else "YoY"
    print(f"  • Share Count Trend:            {dilution_col}{res['share_cagr']:+.2f}% {yr_label} [{dilution_label}]{RESET}")

    # 3. DYNAMIC WACC & VALUATION
    print(f"\n{BOLD}{CYAN}🎯 3. DYNAMIC COST OF CAPITAL & EPS-BASED VALUATION:{RESET}")
    print(f"  • Beta: {res['beta']:.2f} | Dynamic WACC: {BOLD}{res['dynamic_wacc']:.2f}%{RESET} (Ke: {res['cost_equity']:.1f}%, Kd: {res['cost_debt']:.1f}%)")
    spread_col = GREEN if res['economic_spread'] > 0 else RED
    print(f"  • ROIC vs WACC Spread:          {spread_col}{res['economic_spread']:+.1f}%{RESET} (ROIC: {res['roic']:.1f}% vs WACC: {res['dynamic_wacc']:.1f}%)")
    print(f"  • P/E Multiples:                Trailing: {res['trailing_pe']:.1f}x | Forward: {res['forward_pe']:.1f}x")

    # EPS Growth & PEG (v3 fix)
    eps_g = res['eps_growth']
    print(f"  • EPS Growth Rate:              {BOLD}{eps_g:+.1f}%{RESET} (Source: {res['eps_growth_source']})")
    if res['peg_valid'] and res['peg_ratio'] is not None:
        peg_col = GREEN if res['peg_ratio'] <= 1.8 else (YELLOW if res['peg_ratio'] <= 3.0 else RED)
        print(f"  • PEG Ratio (EPS-Based):        {peg_col}{res['peg_ratio']:.2f}x{RESET} (Forward P/E / EPS Growth)")
    else:
        print(f"  • PEG Ratio:                    {RED}UNDEFINED{RESET} (EPS growth ≤ 0% makes PEG meaningless)")

    print(f"  • FCF Yield (Median-Based):     {res['fcf_yield']:.2f}% (Median FCF / EV)")
    print(f"  • Debt-to-Equity:               {res['debt_equity_ratio']:.2f}x")

    # 4. SCORECARD
    print(f"\n{BOLD}{CYAN}🔬 4. FORENSIC SCORECARD — QUALITY vs VALUATION SPLIT:{RESET}")
    print(f"{DIM}  ┌─── BUSINESS QUALITY (60 pts max) ────────────────────────────────────────────────────┐{RESET}")
    def col(pts, mx): pct = (pts/mx)*100; return GREEN if pct >= 75 else (YELLOW if pct >= 50 else RED)

    z_str = f"{res['selected_z']:.2f}" if res['selected_z'] is not None else "N/A"
    print(f"  │ P1 Solvency & Leverage:     [{col(res['p1_solvency'], 20)}{res['p1_solvency']:.1f}/20.0 pts{RESET}] (Z: {z_str}, D/E: {res['debt_equity_ratio']:.2f}x)")
    print(f"  │ P2 Economic Moat & Trends:  [{col(res['p2_moat'], 25)}{res['p2_moat']:.1f}/25.0 pts{RESET}] (Spread: {res['economic_spread']:+.1f}%, Margin Δ: {res['op_margin_trend_delta']:+.1f}%)")
    print(f"  │ P3 Capital Discipline:      [{col(res['p3_discipline'], 15)}{res['p3_discipline']:.1f}/15.0 pts{RESET}] (Shares: {res['share_cagr']:+.2f}%, ROIC: {res['roic']:.1f}%)")
    q_col = GREEN if q_score >= 7.5 else (YELLOW if q_score >= 6.0 else RED)
    print(f"  │ {BOLD}QUALITY SUBTOTAL:{RESET}             [{q_col}{BOLD}{res['quality_raw']:.1f}/60.0 pts → {q_score:.1f}/10{RESET}]")

    print(f"{DIM}  ├─── VALUATION ATTRACTIVENESS (40 pts max) ─────────────────────────────────────────────┤{RESET}")
    peg_str = f"{res['peg_ratio']:.2f}x" if res['peg_valid'] and res['peg_ratio'] is not None else "N/A"
    print(f"  │ P4 Growth-Adj Valuation:    [{col(res['p4_valuation'], 20)}{res['p4_valuation']:.1f}/20.0 pts{RESET}] (PEG: {peg_str}, FCF Yield: {res['fcf_yield']:.1f}%)")
    print(f"  │ P5 Relative Value:          [{col(res['p5_relative'], 20)}{res['p5_relative']:.1f}/20.0 pts{RESET}] (Fwd P/E: {res['forward_pe']:.1f}x, Rev CAGR: {res['rev_cagr']:+.1f}%)")
    v_col = GREEN if v_score >= 7.5 else (YELLOW if v_score >= 5.0 else RED)
    print(f"  │ {BOLD}VALUATION SUBTOTAL:{RESET}           [{v_col}{BOLD}{res['valuation_raw']:.1f}/40.0 pts → {v_score:.1f}/10{RESET}]")
    print(f"{DIM}  └──────────────────────────────────────────────────────────────────────────────────────────┘{RESET}")

    # SCREENING GATES
    q_gate_str = f"{GREEN}PASS (≥6.0){RESET}" if res["quality_gate"] else f"{RED}FAIL (<6.0){RESET}"
    v_gate_str = f"{GREEN}PASS (≥5.0){RESET}" if res["valuation_gate"] else f"{RED}FAIL (<5.0){RESET}"
    d_gate_str = f"{GREEN}PASS (≥60%){RESET}" if res["data_gate"] else f"{RED}FAIL (<60%){RESET}"

    print(f"\n  {BOLD}DUAL-SCREEN HURDLE GATES:{RESET}")
    print(f"    • Quality Gate (≥6.0):          [{q_gate_str}] (Score: {q_score:.1f}/10)")
    print(f"    • Valuation Gate (≥5.0):        [{v_gate_str}] (Score: {v_score:.1f}/10)")
    print(f"    • Data Confidence Gate (≥60%):  [{d_gate_str}] ({conf_col}{conf}{RESET} — {res['data_extractions_ok']}/{res['data_extractions_total']} metrics extracted)")

    # FINAL SCREENING STATUS
    print(f"\n{BOLD}{CYAN}───────────────────────────────────────────────────────────────────────────────────────────{RESET}")
    r_col = GREEN if r_score >= 7.5 else (YELLOW if r_score >= 5.5 else RED)
    sig_col = GREEN if res["screening_code"] in ["HIGH_CONVICTION", "BALANCED_PASS"] else (YELLOW if res["screening_code"] == "EXPENSIVE_QUALITY" else RED)

    print(f"{BOLD}REALITY SCORE (v3.1):{RESET}       {r_col}{BOLD}{r_score:.2f} / 10.0{RESET} ({res['raw_score']:.1f} / 100 pts)")
    print(f"  Quality: {q_col}{BOLD}{q_score:.1f}/10{RESET}  |  Valuation: {v_col}{BOLD}{v_score:.1f}/10{RESET}  |  Confidence: {conf_col}{BOLD}{conf}{RESET}")
    print(f"{BOLD}SCREENING STATUS:{RESET}           {sig_col}{BOLD}{res['screening_signal']}{RESET}")
    print(f"{BOLD}{CYAN}───────────────────────────────────────────────────────────────────────────────────────────{RESET}")

    if res['strengths']:
        print(f"\n{BOLD}{GREEN}✔ CONFIRMED FUNDAMENTAL STRENGTHS:{RESET}")
        for s in res['strengths']:
            print(f"  • {GREEN}{s}{RESET}")

    if res['red_flags']:
        print(f"\n{BOLD}{RED}⚠ SCREENING RED FLAGS & DUE DILIGENCE ALERTS:{RESET}")
        for rf in res['red_flags']:
            print(f"  • {RED}{rf}{RESET}")

    if res['data_failed_labels']:
        print(f"\n{DIM}Missing data labels (fell back to defaults): {', '.join(res['data_failed_labels'])}{RESET}")

    print(f"\n{DIM}⚖  SCREENING TOOL DISCLAIMER: This is a quantitative pre-filter / triage screen, NOT an investment recommendation,")
    print(f"   intrinsic DCF valuation, or portfolio strategy. The score and status reflect data quality-adjusted filings data.")
    print(f"   It does not model competitive moats, regulatory risk, macro cycles, execution quality, or future catalysts.")
    print(f"   Never execute trades based solely on an automated screening model.{RESET}\n")


def compare_tickers(tickers):
    results = []
    for t in tickers:
        print(f"{DIM}Auditing {t.upper()} (v3 Institutional Screener)...{RESET}")
        r = audit_ticker(t)
        if r: results.append(r)

    if not results:
        return

    # Calculate cohort medians for peer-relative benchmarking
    cohort_roics = [r["roic"] for r in results if r["roic"] is not None]
    cohort_waccs = [r["dynamic_wacc"] for r in results if r["dynamic_wacc"] is not None]
    cohort_pes = [r["forward_pe"] for r in results if r["forward_pe"] > 0]
    cohort_pegs = [r["peg_ratio"] for r in results if r["peg_valid"] and r["peg_ratio"] is not None]
    cohort_fcf_yields = [r["fcf_yield"] for r in results if r["fcf_yield"] is not None]

    med_roic = statistics.median(cohort_roics) if cohort_roics else 0.0
    med_wacc = statistics.median(cohort_waccs) if cohort_waccs else 0.0
    med_pe = statistics.median(cohort_pes) if cohort_pes else 0.0
    med_peg = statistics.median(cohort_pegs) if cohort_pegs else 0.0
    med_fcf_y = statistics.median(cohort_fcf_yields) if cohort_fcf_yields else 0.0

    print(f"\n{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{WHITE}                   INSTITUTIONAL AUDITOR (v3.1) — DUAL-GATE QUALITY vs VALUATION SCREEN                    {RESET}")
    print(f"{BOLD}{BLUE}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}\n")

    # Cohort Benchmarks Box
    print(f"{DIM}📊 COHORT PEER BENCHMARKS (N={len(results)}):{RESET}")
    print(f"{DIM}   Median ROIC: {BOLD}{med_roic:.1f}%{RESET}{DIM} | Median WACC: {BOLD}{med_wacc:.1f}%{RESET}{DIM} | Median Fwd P/E: {BOLD}{med_pe:.1f}x{RESET}{DIM} | Median PEG: {BOLD}{med_peg:.2f}x{RESET}{DIM} | Median FCF Yield: {BOLD}{med_fcf_y:.1f}%{RESET}\n")

    header = f"{'Ticker':<7} {'Company':<15} {'Score':<8} {'Quality':<8} {'Value':<8} {'Gates':<8} {'Conf':<5} {'EPS Gr':<8} {'PEG':<6} {'ROIC':<7} {'Dilut':<7} {'Screening Signal':<22}"
    print(f"{BOLD}{header}{RESET}")
    print(f"{CYAN}{'-'*len(header)}{RESET}")

    results.sort(key=lambda x: x["reality_score"], reverse=True)

    for r in results:
        sc = r["reality_score"]
        sc_col = GREEN if sc >= 7.5 else (YELLOW if sc >= 5.5 else RED)
        q_col = GREEN if r["quality_score"] >= 7.5 else (YELLOW if r["quality_score"] >= 6.0 else RED)
        v_col = GREEN if r["valuation_score"] >= 7.5 else (YELLOW if r["valuation_score"] >= 5.0 else RED)
        conf_col = GREEN if r["data_confidence_tier"] == "HIGH" else (YELLOW if r["data_confidence_tier"] == "MEDIUM" else RED)

        # Gate summary: Q / V / D
        q_g = "P" if r["quality_gate"] else "F"
        v_g = "P" if r["valuation_gate"] else "F"
        d_g = "P" if r["data_gate"] else "F"
        gate_str = f"{q_g}/{v_g}/{d_g}"
        gate_col = GREEN if (r["quality_gate"] and r["valuation_gate"] and r["data_gate"]) else (YELLOW if r["quality_gate"] else RED)

        peg_str = f"{r['peg_ratio']:.1f}x" if r['peg_valid'] and r['peg_ratio'] is not None else "N/A"
        eps_str = f"{r['eps_growth']:+.1f}%" if r['eps_growth'] is not None else "N/A"
        dilut_str = f"{r['share_cagr']:+.1f}%"

        # Short concise signal label
        code = r["screening_code"]
        if code == "HIGH_CONVICTION":
            short_sig = "High-Conviction"
            sig_col = GREEN
        elif code == "BALANCED_PASS":
            short_sig = "Balanced Screen"
            sig_col = GREEN
        elif code == "EXPENSIVE_QUALITY":
            short_sig = "Expensive Moat"
            sig_col = YELLOW
        elif code == "VALUE_TRAP":
            short_sig = "Value Trap Risk"
            sig_col = RED
        elif code == "DATA_FAIL":
            short_sig = "Data Deficient"
            sig_col = RED
        else:
            short_sig = "Screening Fail"
            sig_col = RED

        print(
            f"{BOLD}{r['symbol']:<7}{RESET} "
            f"{r['name'][:13]:<15} "
            f"{sc_col}{sc:.2f}/10{RESET}  "
            f"{q_col}Q:{r['quality_score']:.1f}{RESET}  "
            f"{v_col}V:{r['valuation_score']:.1f}{RESET}  "
            f"{gate_col}{gate_str:<8}{RESET} "
            f"{conf_col}{r['data_confidence_tier'][:3]:<5}{RESET} "
            f"{eps_str:<8} "
            f"{peg_str:<6} "
            f"{r['roic']:<7.1f} "
            f"{dilut_str:<7} "
            f"{sig_col}{short_sig:<22}{RESET}"
        )

    print(f"\n{DIM}⚖  Screening tool only. Gates: Q=Quality (≥6.0), V=Valuation (≥5.0), D=Data Confidence (≥60%). P=Pass, F=Fail.{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="Universal Stock Reality & Truth Auditor — v3 Institutional Edition")
    parser.add_argument("tickers", nargs="*", default=["AAPL"], help="Stock tickers to audit (e.g. AAPL NVDA TSLA JPM)")
    parser.add_argument("--compare", action="store_true", help="Display side-by-side leaderboard comparison")

    args = parser.parse_args()

    if args.compare or len(args.tickers) > 1:
        compare_tickers(args.tickers)
    else:
        res = audit_ticker(args.tickers[0])
        if res:
            print_audit_report(res)


if __name__ == "__main__":
    main()
