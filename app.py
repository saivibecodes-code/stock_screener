#!/usr/bin/env python3
"""
Quantitative Reality Screener & Multi-Strategy Portfolio Engine
Streamlit Web Application for Institutional Equity & Sector Analysis
"""

import os
import sys
import json
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup dynamic path resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DIVIDEND_DIR = os.path.join(BASE_DIR, "dividend_strategy")
if DIVIDEND_DIR not in sys.path:
    sys.path.insert(0, DIVIDEND_DIR)

SECTOR_DIR = os.path.join(BASE_DIR, "sector_etf_strategy")
if SECTOR_DIR not in sys.path:
    sys.path.insert(0, SECTOR_DIR)

# Strategy Imports
try:
    from stock_reality_auditor import audit_ticker
except Exception as e:
    audit_ticker = None

try:
    from top200_universe_screener import run_top200_scan, TOP_200_UNIVERSE
except Exception as e:
    run_top200_scan = None
    TOP_200_UNIVERSE = []

try:
    from dividend_strategy.dividend_reality_auditor import DividendRealityAuditor, audit_dividend_stock
    from dividend_strategy.dividend_screener import run_dividend_screen, DIVIDEND_UNIVERSE
    from dividend_strategy.dividend_portfolio_agent import DividendPortfolioAgent
except Exception as e:
    DividendRealityAuditor = None
    audit_dividend_stock = None
    run_dividend_screen = None
    DIVIDEND_UNIVERSE = []
    DividendPortfolioAgent = None

try:
    from sector_etf_strategy.sector_etf_analyzer import SectorETFAnalyzer
    from sector_etf_strategy.sector_etf_screener import run_sector_screen, GICS_SECTOR_ETFS, THEMATIC_ETFS
    from sector_etf_strategy.sector_rotation_portfolio import SectorRotationAgent
except Exception as e:
    SectorETFAnalyzer = None
    run_sector_screen = None
    SectorRotationAgent = None
    GICS_SECTOR_ETFS = {}
    THEMATIC_ETFS = {}

# Page Configuration
st.set_page_config(
    page_title="Institutional Reality Screener & Strategy Suite",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #3b82f6, #10b981, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #9ca3af;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
    .badge-pass {
        background-color: #065f46;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-fail {
        background-color: #7f1d1d;
        color: #f87171;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 8px 8px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Data Loading & Caching Helpers
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_top200_data() -> pd.DataFrame:
    cache_path = os.path.join(BASE_DIR, ".cache_top200.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                return df
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_dividend_data() -> pd.DataFrame:
    cache_path = os.path.join(BASE_DIR, ".cache_dividend.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                return df
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_sector_data() -> pd.DataFrame:
    cache_path = os.path.join(BASE_DIR, ".cache_sector.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                return df
        except Exception:
            pass
    return pd.DataFrame()


def load_portfolio_json(filepath: str) -> dict:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


# -----------------------------------------------------------------------------
# Sidebar Configuration
# -----------------------------------------------------------------------------

with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/combo-chart.png", width=64)
    st.markdown("### **QUANTITATIVE REALITY SUITE**")
    st.caption("Institutional Screening, Dividend Fortress & Sector Rotation")
    st.markdown("---")

    st.markdown("#### **Active Data Sources**")
    top200_cache_exists = os.path.exists(os.path.join(BASE_DIR, ".cache_top200.json"))
    dividend_cache_exists = os.path.exists(os.path.join(BASE_DIR, ".cache_dividend.json"))
    sector_cache_exists = os.path.exists(os.path.join(BASE_DIR, ".cache_sector.json"))

    st.write(f"• **Top 200 Cache:** {'🟢 Available' if top200_cache_exists else '🔴 Missing'}")
    st.write(f"• **Dividend Cache:** {'🟢 Available' if dividend_cache_exists else '🔴 Missing'}")
    st.write(f"• **Sector Cache:** {'🟢 Available' if sector_cache_exists else '🔴 Missing'}")

    st.markdown("---")
    if st.button("🔄 Clear App Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("App cache cleared successfully!")
        st.rerun()

    st.markdown("---")
    st.markdown("""
    **Hurdle Criteria Summary:**
    - **Dual-Gate Screener**: Quality ≥ 6.0, Valuation ≥ 5.0, Data ≥ 60%
    - **Dividend Fortress**: Yield ≥ 2.5%, Streak ≥ 10y, FCF Payout ≤ 70%, Safety ≥ 70
    - **Sector Rotation**: SPY vs 200 SMA Trend + RS-Ratio Momentum
    """)
    st.caption("Quantitative Reality Engine v3.2")


# -----------------------------------------------------------------------------
# Main Header & Tab Layout
# -----------------------------------------------------------------------------

st.markdown('<div class="main-header">Institutional Reality Screener & Strategy Suite</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-sector fundamental auditing, forensic cash flow analysis, and systematic asset allocation</div>', unsafe_allow_html=True)

tab_top200, tab_dividend, tab_sector, tab_portfolio, tab_audit = st.tabs([
    "🏆 Top 200 Reality Screener",
    "🛡️ Dividend Fortress Strategy",
    "🌐 Sector ETF Rotation",
    "💼 Active Model Portfolios",
    "🔍 Single-Stock Deep Dive"
])


# =============================================================================
# TAB 1: TOP 200 REALITY SCREENER
# =============================================================================

with tab_top200:
    st.subheader("Dual-Gate Institutional Reality Screener")
    st.caption("Rigorous audit of the Top 200 US market champions across Quality (ROIC, Moat, Balance Sheet) and Valuation (FCF Yield, Relative Value).")

    df_top200 = load_top200_data()

    if df_top200.empty:
        st.warning("No pre-computed Top 200 audit data found in cache. Click below to initiate universe scan.")
        if st.button("🚀 Run Top 200 Universe Scan", type="primary"):
            with st.spinner("Screening Top 200 universe with 16 threads... this takes ~20 seconds..."):
                if run_top200_scan:
                    res_df = run_top200_scan(max_workers=16)
                    st.success("Screen complete!")
                    st.rerun()
                else:
                    st.error("Scanner module unavailable.")
    else:
        # Determine dual-gate passing
        if "passed_dual_gate" not in df_top200.columns:
            if "screening_code" in df_top200.columns:
                df_top200["passed_dual_gate"] = df_top200["screening_code"].isin(["HIGH_CONVICTION", "BALANCED_PASS"])
            else:
                df_top200["passed_dual_gate"] = (df_top200["quality_score"] >= 6.0) & (df_top200["valuation_score"] >= 5.0)

        # Top Summary KPIs
        total_stocks = len(df_top200)
        passed_count = int(df_top200["passed_dual_gate"].sum())
        pass_pct = (passed_count / total_stocks) * 100 if total_stocks else 0
        avg_quality = df_top200["quality_score"].mean()
        avg_valuation = df_top200["valuation_score"].mean()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{total_stocks}</div><div class="metric-label">Universe Screened</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#10b981;">{passed_count} ({pass_pct:.1f}%)</div><div class="metric-label">Dual-Gate Passed</div></div>', unsafe_allow_html=True)
        with col3:
            high_conv_count = int((df_top200["screening_code"] == "HIGH_CONVICTION").sum()) if "screening_code" in df_top200.columns else 0
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#3b82f6;">{high_conv_count}</div><div class="metric-label">High Conviction</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_quality:.1f} / 10</div><div class="metric-label">Avg Quality Score</div></div>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_valuation:.1f} / 10</div><div class="metric-label">Avg Valuation Score</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Filters Row
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 2, 1.5, 1.5])
        with f_col1:
            pass_only = st.checkbox("Passed Dual-Gate Only", value=False)
        with f_col2:
            all_sectors = sorted([s for s in df_top200["sector"].dropna().unique() if s])
            selected_sectors = st.multiselect("Filter by Sector", options=all_sectors, default=[])
        with f_col3:
            min_qual = st.slider("Min Quality Score", min_value=0.0, max_value=10.0, value=0.0, step=0.5)
        with f_col4:
            search_ticker = st.text_input("Search Symbol / Name", value="").strip().upper()

        # Apply Filters
        filtered_df = df_top200.copy()
        if pass_only:
            filtered_df = filtered_df[filtered_df["passed_dual_gate"] == True]
        if selected_sectors:
            filtered_df = filtered_df[filtered_df["sector"].isin(selected_sectors)]
        if min_qual > 0:
            filtered_df = filtered_df[filtered_df["quality_score"] >= min_qual]
        if search_ticker:
            filtered_df = filtered_df[
                filtered_df["symbol"].str.contains(search_ticker, na=False) |
                filtered_df["name"].str.upper().str.contains(search_ticker, na=False)
            ]

        # Interactive Visualizations
        st.markdown("#### **Quality vs. Valuation Matrix**")
        viz_col1, viz_col2 = st.columns([2.2, 1])

        with viz_col1:
            fig_scatter = px.scatter(
                filtered_df,
                x="quality_score",
                y="valuation_score",
                color="screening_code" if "screening_code" in filtered_df.columns else "passed_dual_gate",
                hover_name="symbol",
                hover_data={"name": True, "sector": True, "roic": ":.1f%", "fcf_yield": ":.1f%", "quality_score": ":.1f", "valuation_score": ":.1f"},
                title="Institutional Matrix: Quality Gate (X ≥ 6.0) vs Valuation Gate (Y ≥ 5.0)",
                labels={"quality_score": "Quality Score (0-10)", "valuation_score": "Valuation Score (0-10)", "screening_code": "Screening Signal"},
                color_discrete_map={
                    "HIGH_CONVICTION": "#10b981",
                    "BALANCED_PASS": "#3b82f6",
                    "QUALITY_PREMIUM_OVERVALUED": "#f59e0b",
                    "VALUE_TRAP_RISK": "#ec4899",
                    "UNINVESTABLE": "#ef4444"
                }
            )
            # Threshold lines
            fig_scatter.add_vline(x=6.0, line_dash="dash", line_color="rgba(255, 255, 255, 0.4)", annotation_text="Quality Gate (6.0)")
            fig_scatter.add_hline(y=5.0, line_dash="dash", line_color="rgba(255, 255, 255, 0.4)", annotation_text="Valuation Gate (5.0)")
            fig_scatter.update_layout(template="plotly_dark", height=420, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_scatter, use_container_width=True)

        with viz_col2:
            if "sector" in filtered_df.columns and not filtered_df.empty:
                sector_counts = filtered_df[filtered_df["passed_dual_gate"] == True]["sector"].value_counts().reset_index()
                sector_counts.columns = ["Sector", "Passed Stocks"]
                fig_sector = px.bar(
                    sector_counts,
                    x="Passed Stocks",
                    y="Sector",
                    orientation="h",
                    title="Passed Stocks by Sector",
                    color="Passed Stocks",
                    color_continuous_scale="Viridis"
                )
                fig_sector.update_layout(template="plotly_dark", height=420, margin=dict(l=20, r=20, t=40, b=20), yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_sector, use_container_width=True)

        # Tabular View
        st.markdown(f"#### **Audited Stocks Directory ({len(filtered_df)} shown)**")
        display_cols = [
            "symbol", "name", "price", "sector", "quality_score", "valuation_score",
            "reality_score", "roic", "fcf_yield", "selected_z", "screening_code"
        ]
        available_cols = [c for c in display_cols if c in filtered_df.columns]
        table_df = filtered_df[available_cols].copy()

        # Format percentages and floats
        if "price" in table_df.columns:
            table_df["price"] = table_df["price"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
        if "roic" in table_df.columns:
            table_df["roic"] = table_df["roic"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
        if "fcf_yield" in table_df.columns:
            table_df["fcf_yield"] = table_df["fcf_yield"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
        if "selected_z" in table_df.columns:
            table_df["selected_z"] = table_df["selected_z"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
        if "quality_score" in table_df.columns:
            table_df["quality_score"] = table_df["quality_score"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")
        if "valuation_score" in table_df.columns:
            table_df["valuation_score"] = table_df["valuation_score"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")
        if "reality_score" in table_df.columns:
            table_df["reality_score"] = table_df["reality_score"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")

        st.dataframe(table_df, use_container_width=True, height=450)

        # CSV Export
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Screener Data (CSV)",
            data=csv_data,
            file_name="top200_reality_screener.csv",
            mime="text/csv"
        )


# =============================================================================
# TAB 2: DIVIDEND FORTRESS STRATEGY
# =============================================================================

with tab_dividend:
    st.subheader("Dividend Fortress & Sustainable Income Engine")
    st.caption("Comprehensive analysis of Dividend Aristocrats, Kings, and High-Yield stalwarts audited for cash flow coverage, Chowder Rule, and dividend cut risk.")

    df_div = load_dividend_data()

    if df_div.empty:
        st.warning("No pre-computed Dividend Fortress data found. Click below to screen the dividend universe.")
        if st.button("🚀 Run Dividend Universe Scan", type="primary"):
            with st.spinner("Screening 74 dividend champions..."):
                if run_dividend_screen:
                    res_div = run_dividend_screen(max_workers=16)
                    st.success("Dividend screen complete!")
                    st.rerun()
                else:
                    st.error("Dividend screener module unavailable.")
    else:
        # Summary KPIs
        total_div = len(df_div)
        aristocrats = int(df_div["is_aristocrat"].sum()) if "is_aristocrat" in df_div.columns else 0
        kings = int(df_div["is_king"].sum()) if "is_king" in df_div.columns else 0
        avg_yield = df_div["dividend_yield_pct"].mean() if "dividend_yield_pct" in df_div.columns else 0
        avg_safety = df_div["safety_score"].mean() if "safety_score" in df_div.columns else 0
        fortress_count = int((df_div["tier"] == "TIER_1_FORTRESS").sum()) if "tier" in df_div.columns else 0

        d_col1, d_col2, d_col3, d_col4, d_col5 = st.columns(5)
        with d_col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{total_div}</div><div class="metric-label">Champions Monitored</div></div>', unsafe_allow_html=True)
        with d_col2:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#10b981;">{fortress_count}</div><div class="metric-label">Tier 1 Fortress</div></div>', unsafe_allow_html=True)
        with d_col3:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#3b82f6;">{aristocrats} (Kings: {kings})</div><div class="metric-label">Aristocrats (25y+)</div></div>', unsafe_allow_html=True)
        with d_col4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_yield:.2f}%</div><div class="metric-label">Average Yield</div></div>', unsafe_allow_html=True)
        with d_col5:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_safety:.1f} / 100</div><div class="metric-label">Avg Safety Score</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Filters
        df_col1, df_col2, df_col3, df_col4 = st.columns([1.5, 1.5, 1.5, 1.5])
        with df_col1:
            min_yield = st.slider("Min Dividend Yield (%)", min_value=0.0, max_value=8.0, value=2.0, step=0.25)
        with df_col2:
            min_safety = st.slider("Min Safety Score", min_value=0, max_value=100, value=60, step=5)
        with df_col3:
            aristocrats_only = st.checkbox("Aristocrats (25y+) Only", value=False)
            no_cuts = st.checkbox("Exclude Dividend Cuts (5y)", value=True)
        with df_col4:
            div_search = st.text_input("Search Dividend Symbol", value="").strip().upper()

        # Apply Filters
        filtered_div = df_div.copy()
        if min_yield > 0 and "dividend_yield_pct" in filtered_div.columns:
            filtered_div = filtered_div[filtered_div["dividend_yield_pct"] >= min_yield]
        if min_safety > 0 and "safety_score" in filtered_div.columns:
            filtered_div = filtered_div[filtered_div["safety_score"] >= min_safety]
        if aristocrats_only and "is_aristocrat" in filtered_div.columns:
            filtered_div = filtered_div[filtered_div["is_aristocrat"] == True]
        if no_cuts and "cut_in_last_5y" in filtered_div.columns:
            filtered_div = filtered_div[filtered_div["cut_in_last_5y"] == False]
        if div_search:
            filtered_div = filtered_div[
                filtered_div["symbol"].str.contains(div_search, na=False) |
                filtered_div["name"].str.upper().str.contains(div_search, na=False)
            ]

        # Charts Row
        st.markdown("#### **Yield vs. Growth Profile (The Chowder Plane)**")
        dc_col1, dc_col2 = st.columns([2.2, 1])

        with dc_col1:
            fig_div_scatter = px.scatter(
                filtered_div,
                x="dividend_yield_pct",
                y="cagr_5y_pct",
                size="safety_score",
                color="tier",
                hover_name="symbol",
                hover_data={
                    "name": True,
                    "chowder_number": ":.2f%",
                    "fcf_payout_ratio": ":.1f%",
                    "streak_years": True,
                    "safety_score": True
                },
                title="Yield % (X) vs 5-Year Dividend CAGR % (Y) | Bubble Size = Safety Score",
                labels={"dividend_yield_pct": "Current Dividend Yield (%)", "cagr_5y_pct": "5-Year Dividend CAGR (%)", "tier": "Fortress Tier"},
                color_discrete_map={
                    "TIER_1_FORTRESS": "#10b981",
                    "TIER_2_BALANCED": "#3b82f6",
                    "TIER_3_SPECULATIVE": "#f59e0b",
                    "CRITERIA_FAILS": "#ef4444"
                }
            )
            fig_div_scatter.update_layout(template="plotly_dark", height=420, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_div_scatter, use_container_width=True)

        with dc_col2:
            if "tier" in filtered_div.columns:
                tier_dist = filtered_div["tier"].value_counts().reset_index()
                tier_dist.columns = ["Tier", "Count"]
                fig_tier = px.pie(
                    tier_dist,
                    names="Tier",
                    values="Count",
                    title="Dividend Safety Tiers",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_tier.update_layout(template="plotly_dark", height=420, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_tier, use_container_width=True)

        # Tabular View
        st.markdown(f"#### **Dividend Champions Directory ({len(filtered_div)} shown)**")
        div_display_cols = [
            "symbol", "name", "sector", "price", "dividend_yield_pct", "cagr_5y_pct",
            "chowder_number", "fcf_payout_ratio", "streak_years", "safety_score", "tier"
        ]
        available_div_cols = [c for c in div_display_cols if c in filtered_div.columns]
        div_table = filtered_div[available_div_cols].copy()

        if "price" in div_table.columns:
            div_table["price"] = div_table["price"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
        if "dividend_yield_pct" in div_table.columns:
            div_table["dividend_yield_pct"] = div_table["dividend_yield_pct"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
        if "cagr_5y_pct" in div_table.columns:
            div_table["cagr_5y_pct"] = div_table["cagr_5y_pct"].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "N/A")
        if "chowder_number" in div_table.columns:
            div_table["chowder_number"] = div_table["chowder_number"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
        if "fcf_payout_ratio" in div_table.columns:
            div_table["fcf_payout_ratio"] = div_table["fcf_payout_ratio"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) and x is not None else "N/A")
        if "safety_score" in div_table.columns:
            div_table["safety_score"] = div_table["safety_score"].apply(lambda x: f"{x:.0f}" if pd.notnull(x) else "N/A")

        st.dataframe(div_table, use_container_width=True, height=450)

        # CSV Export
        csv_div = filtered_div.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Dividend Screener Data (CSV)",
            data=csv_div,
            file_name="dividend_fortress_screener.csv",
            mime="text/csv"
        )


# =============================================================================
# TAB 3: SECTOR ETF ROTATION
# =============================================================================

with tab_sector:
    st.subheader("Tactical Sector ETF Rotation Engine")
    st.caption("Quantitative sector rotation driven by 200-day SMA market safety regime, Relative Rotation Graph (RRG) momentum, and GICS valuation fundamentals.")

    df_sec = load_sector_data()

    if df_sec.empty:
        st.warning("No pre-computed Sector ETF data found in cache. Click below to run the sector rotation scan.")
        if st.button("🚀 Run Sector ETF Scan", type="primary"):
            with st.spinner("Analyzing 19 Sector & Thematic ETFs..."):
                if run_sector_screen:
                    gics, them = run_sector_screen(include_thematics=True, max_workers=16)
                    st.success("Sector screen complete!")
                    st.rerun()
                else:
                    st.error("Sector screener module unavailable.")
    else:
        # Market Regime Detection
        regime_status = "BULL_MARKET"
        spy_price = 0.0
        spy_sma = 0.0
        spy_dist = 0.0

        try:
            agent = SectorRotationAgent()
            reg_info = agent.check_market_regime()
            regime_status = reg_info.get("regime", "BULL_MARKET")
            spy_price = reg_info.get("spy_price", 0.0)
            spy_sma = reg_info.get("spy_200_sma", 0.0)
            spy_dist = reg_info.get("dist_pct", 0.0)
        except Exception:
            pass

        # Regime Banner
        is_bull = (regime_status == "BULL_MARKET")
        reg_col = "#10b981" if is_bull else "#ef4444"
        reg_desc = "Offensive Growth & Cyclicals: Top 3 Sectors + 1 Thematic (95% Allocated, 5% Cash Reserve)" if is_bull else "Capital Preservation & Flight-to-Safety: 40% Cash Buffer + Defensive Ballast (XLV, XLP, XLU)"

        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.7); border-left: 6px solid {reg_col}; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 0.9rem; color: #94a3b8; text-transform: uppercase;">Current Market Regime Filter:</span>
                    <h3 style="margin: 2px 0 0 0; color: {reg_col}; font-weight: 800;">{regime_status}</h3>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 0.85rem; color: #94a3b8;">SPY: <b>${spy_price:.2f}</b> vs 200 SMA: <b>${spy_sma:.2f}</b></span><br>
                    <span style="font-size: 1.1rem; font-weight: 700; color: {reg_col};">{spy_dist:+.2f}% Spread</span>
                </div>
            </div>
            <div style="margin-top: 8px; font-size: 0.9rem; color: #cbd5e1;"><b>Tactical Mandate:</b> {reg_desc}</div>
        </div>
        """, unsafe_allow_html=True)

        # Unpack technicals & momentum for clean plotting
        plot_rows = []
        for _, row in df_sec.iterrows():
            tech = row.get("technicals") or {}
            mom = row.get("relative_momentum") or {}
            fund = row.get("fundamentals") or {}
            plot_rows.append({
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "category": row.get("category"),
                "composite_score": row.get("composite_score", 0.0),
                "action": row.get("action", "NEUTRAL"),
                "price": tech.get("current_price", 0.0),
                "ret_3m": tech.get("return_3m_pct", 0.0),
                "ret_6m": tech.get("return_6m_pct", 0.0),
                "rsi_14": tech.get("rsi_14", 50.0),
                "rs_ratio": mom.get("rs_ratio", 100.0),
                "rs_momentum": mom.get("rs_momentum", 100.0),
                "rrg_quadrant": mom.get("rrg_quadrant", "UNKNOWN"),
                "pe_ratio": fund.get("pe_ratio", None)
            })

        df_sec_flat = pd.DataFrame(plot_rows)

        # Visualizations
        sec_col1, sec_col2 = st.columns([1.6, 1.4])

        with sec_col1:
            st.markdown("#### **Relative Rotation Graph (RRG vs. SPY)**")
            fig_rrg = px.scatter(
                df_sec_flat,
                x="rs_ratio",
                y="rs_momentum",
                color="rrg_quadrant",
                text="symbol",
                hover_name="name",
                hover_data={"action": True, "composite_score": True, "ret_3m": ":.1f%", "rsi_14": ":.1f"},
                title="RRG Quadrants: RS-Ratio (X) vs RS-Momentum (Y)",
                labels={"rs_ratio": "RS-Ratio (Benchmark = 100)", "rs_momentum": "RS-Momentum (Trend = 100)", "rrg_quadrant": "RRG Stage"},
                color_discrete_map={
                    "LEADING": "#10b981",
                    "IMPROVING": "#3b82f6",
                    "WEAKENING": "#f59e0b",
                    "LAGGING": "#ef4444"
                }
            )
            # Add center crosshairs at (100, 100)
            fig_rrg.add_vline(x=100.0, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)")
            fig_rrg.add_hline(y=100.0, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)")
            fig_rrg.update_traces(textposition="top center")
            fig_rrg.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_rrg, use_container_width=True)

        with sec_col2:
            st.markdown("#### **Sector Composite Allocation Ranking**")
            df_sec_sorted = df_sec_flat.sort_values(by="composite_score", ascending=True)
            fig_bar = px.bar(
                df_sec_sorted,
                x="composite_score",
                y="symbol",
                color="action",
                orientation="h",
                text="composite_score",
                hover_name="name",
                title="Composite Ranking (0 to 100 Points)",
                labels={"composite_score": "Composite Score", "symbol": "Sector ETF", "action": "Tactical Action"},
                color_discrete_map={
                    "STRONG_OVERWEIGHT": "#10b981",
                    "OVERWEIGHT": "#34d399",
                    "NEUTRAL": "#94a3b8",
                    "UNDERWEIGHT": "#f59e0b",
                    "AVOID": "#ef4444"
                }
            )
            fig_bar.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig_bar.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)

        # Tabular View
        st.markdown("#### **Sector ETF Intelligence Ledger**")
        disp_sec = df_sec_flat[[
            "symbol", "name", "category", "price", "ret_3m", "ret_6m",
            "rsi_14", "rs_ratio", "rrg_quadrant", "composite_score", "action"
        ]].copy()

        disp_sec["price"] = disp_sec["price"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
        disp_sec["ret_3m"] = disp_sec["ret_3m"].apply(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "N/A")
        disp_sec["ret_6m"] = disp_sec["ret_6m"].apply(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "N/A")
        disp_sec["rsi_14"] = disp_sec["rsi_14"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")
        disp_sec["rs_ratio"] = disp_sec["rs_ratio"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
        disp_sec["composite_score"] = disp_sec["composite_score"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")

        st.dataframe(disp_sec, use_container_width=True, height=450)


# =============================================================================
# TAB 4: ACTIVE MODEL PORTFOLIOS
# =============================================================================

with tab_portfolio:
    st.subheader("Active Model Paper Portfolios & Ledgers")
    st.caption("Live tracking of $1,000 algorithmic paper allocations across the 3 core quantitative disciplines.")

    portfolio_choice = st.radio(
        "Select Model Portfolio Strategy:",
        options=["🏆 Top 200 Reality Screener ($1,000)", "🛡️ Dividend Fortress ($1,000)", "🌐 Tactical Sector ETF Rotation ($1,000)"],
        horizontal=True
    )

    if "Top 200" in portfolio_choice:
        port_file = os.path.join(BASE_DIR, "paper_portfolio.json")
        port_data = load_portfolio_json(port_file)
        strat_name = "Top 200 Reality Screener"
    elif "Dividend" in portfolio_choice:
        port_file = os.path.join(DIVIDEND_DIR, "dividend_portfolio.json")
        port_data = load_portfolio_json(port_file)
        strat_name = "Dividend Fortress"
    else:
        port_file = os.path.join(SECTOR_DIR, "sector_portfolio.json")
        port_data = load_portfolio_json(port_file)
        strat_name = "Sector ETF Rotation"

    if not port_data or "positions" not in port_data:
        st.info(f"No active positions recorded for {strat_name}. Ledger file: `{os.path.basename(port_file)}`")
    else:
        cash = port_data.get("cash", 0.0)
        positions = port_data.get("positions", {})
        created_at = port_data.get("created_at", "N/A")
        last_updated = port_data.get("last_updated", "N/A")

        # Compute current portfolio metrics
        pos_rows = []
        total_invested = 0.0
        total_current_val = 0.0

        for sym, p in positions.items():
            shares = p.get("shares", 0.0)
            cost_basis = p.get("cost_basis", 0.0) or p.get("buy_price", 0.0)
            cur_price = p.get("current_price", cost_basis)
            mkt_val = shares * cur_price
            invested = shares * cost_basis
            unrealized_pnl = mkt_val - invested
            unrealized_pct = (unrealized_pnl / invested * 100.0) if invested > 0 else 0.0

            total_invested += invested
            total_current_val += mkt_val

            pos_rows.append({
                "Symbol": sym,
                "Company / Sector": p.get("name", p.get("sector", sym)),
                "Shares": shares,
                "Cost Basis": cost_basis,
                "Current Price": cur_price,
                "Invested": invested,
                "Market Value": mkt_val,
                "Unrealized P&L ($)": unrealized_pnl,
                "Unrealized P&L (%)": unrealized_pct
            })

        total_portfolio_val = total_current_val + cash
        total_cost = total_invested + cash
        net_pnl = total_portfolio_val - total_cost
        net_pnl_pct = (net_pnl / total_cost * 100.0) if total_cost > 0 else 0.0

        # Portfolio KPI Cards
        pk1, pk2, pk3, pk4 = st.columns(4)
        with pk1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">${total_portfolio_val:,.2f}</div><div class="metric-label">Total Portfolio Value</div></div>', unsafe_allow_html=True)
        with pk2:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#10b981;">${cash:,.2f}</div><div class="metric-label">Cash Buffer</div></div>', unsafe_allow_html=True)
        with pk3:
            pnl_col = "#10b981" if net_pnl >= 0 else "#ef4444"
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{pnl_col};">${net_pnl:+,.2f} ({net_pnl_pct:+.2f}%)</div><div class="metric-label">Unrealized P&L</div></div>', unsafe_allow_html=True)
        with pk4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{len(positions)}</div><div class="metric-label">Active Holdings</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Visualizations
        if pos_rows:
            df_pos = pd.DataFrame(pos_rows)
            df_pos["Weight (%)"] = (df_pos["Market Value"] / total_portfolio_val) * 100.0

            p_viz1, p_viz2 = st.columns([1.5, 1.5])
            with p_viz1:
                donut_labels = list(df_pos["Symbol"]) + ["USD CASH"]
                donut_values = list(df_pos["Market Value"]) + [cash]
                fig_donut = px.pie(
                    names=donut_labels,
                    values=donut_values,
                    title="Portfolio Capital Allocation Breakdown",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_donut.update_layout(template="plotly_dark", height=380, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_donut, use_container_width=True)

            with p_viz2:
                fig_pnl = px.bar(
                    df_pos.sort_values(by="Unrealized P&L (%)", ascending=False),
                    x="Symbol",
                    y="Unrealized P&L (%)",
                    color="Unrealized P&L (%)",
                    color_continuous_scale=["#ef4444", "#3b82f6", "#10b981"],
                    title="Position Performance Distribution (%)"
                )
                fig_pnl.update_layout(template="plotly_dark", height=380, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_pnl, use_container_width=True)

            # Positions Table
            st.markdown("#### **Active Holdings Ledger**")
            disp_pos = df_pos.copy()
            disp_pos["Shares"] = disp_pos["Shares"].apply(lambda x: f"{x:.4f}")
            disp_pos["Cost Basis"] = disp_pos["Cost Basis"].apply(lambda x: f"${x:,.2f}")
            disp_pos["Current Price"] = disp_pos["Current Price"].apply(lambda x: f"${x:,.2f}")
            disp_pos["Invested"] = disp_pos["Invested"].apply(lambda x: f"${x:,.2f}")
            disp_pos["Market Value"] = disp_pos["Market Value"].apply(lambda x: f"${x:,.2f}")
            disp_pos["Weight (%)"] = disp_pos["Weight (%)"].apply(lambda x: f"{x:.1f}%")
            disp_pos["Unrealized P&L ($)"] = disp_pos["Unrealized P&L ($)"].apply(lambda x: f"${x:+,.2f}")
            disp_pos["Unrealized P&L (%)"] = disp_pos["Unrealized P&L (%)"].apply(lambda x: f"{x:+.2f}%")

            st.dataframe(disp_pos, use_container_width=True)

        # Transactions Drawer
        transactions = port_data.get("transactions", [])
        if transactions:
            with st.expander(f"📜 View Transaction History ({len(transactions)} events)"):
                df_tx = pd.DataFrame(transactions)
                st.dataframe(df_tx, use_container_width=True)


# =============================================================================
# TAB 5: SINGLE-STOCK DEEP DIVE AUDITOR
# =============================================================================

with tab_audit:
    st.subheader("Single-Stock & ETF Institutional Deep Dive")
    st.caption("Perform an on-demand audit across 5 forensic accounting pillars: Solvency, Economic Moat, Capital Discipline, FCF Valuation, and Momentum.")

    a_col1, a_col2 = st.columns([3, 1])
    with a_col1:
        deep_ticker = st.text_input("Enter Ticker Symbol for Forensic Audit", value="AAPL", max_chars=10).strip().upper()
    with a_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_audit_btn = st.button("🔍 Run Full Institutional Audit", type="primary", use_container_width=True)

    if deep_ticker and (run_audit_btn or st.session_state.get("last_audited_ticker") == deep_ticker):
        st.session_state["last_audited_ticker"] = deep_ticker
        with st.spinner(f"Running forensic reality audit on {deep_ticker}..."):
            try:
                res = audit_ticker(deep_ticker) if audit_ticker else None
            except Exception as e:
                res = None
                st.error(f"Audit failed: {e}")

        if res:
            # Header Verdict Card
            sig = res.get("screening_signal", "UNKNOWN")
            q_score = res.get("quality_score", 0.0)
            v_score = res.get("valuation_score", 0.0)
            r_score = res.get("reality_score", 0.0)
            price = res.get("price", 0.0)
            mkt_cap = res.get("mkt_cap", 0.0)

            verdict_color = "#10b981" if "PASS" in sig or "HIGH" in sig else "#f59e0b" if "PREMIUM" in sig else "#ef4444"

            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.8); border: 2px solid {verdict_color}; border-radius: 12px; padding: 20px 24px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                    <div>
                        <span style="font-size: 1.1rem; color: #94a3b8;">{res.get('sector', 'N/A')} • {res.get('industry', 'N/A')}</span>
                        <h2 style="margin: 4px 0 0 0; color: #f8fafc; font-size: 2.2rem;">{res.get('name', deep_ticker)} ({deep_ticker})</h2>
                        <span style="font-size: 1.2rem; font-weight: 700; color: #cbd5e1;">${price:,.2f} USD</span>
                        <span style="font-size: 0.95rem; color: #94a3b8; margin-left: 12px;">Market Cap: ${mkt_cap/1e9:,.1f}B</span>
                    </div>
                    <div style="text-align: right;">
                        <div style="background: {verdict_color}; color: #0f172a; font-weight: 800; font-size: 1rem; padding: 6px 16px; border-radius: 9999px; display: inline-block;">
                            {sig.replace('_', ' ')}
                        </div>
                        <div style="margin-top: 10px; font-size: 1.5rem; font-weight: 800; color: #f8fafc;">
                            Reality Score: {r_score:.1f} / 10
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 5-Pillar Scoreboard
            st.markdown("#### **Forensic 5-Pillar Scorecard**")
            p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns(5)
            with p_c1:
                p1 = res.get("p1_solvency", 0.0)
                st.markdown(f'<div class="metric-card"><div class="metric-value">{p1:.1f} / 2.0</div><div class="metric-label">Pillar 1: Solvency</div><div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">Altman Z: {res.get("selected_z", 0.0):.2f}</div></div>', unsafe_allow_html=True)
            with p_c2:
                p2 = res.get("p2_moat", 0.0)
                st.markdown(f'<div class="metric-card"><div class="metric-value">{p2:.1f} / 2.5</div><div class="metric-label">Pillar 2: Moat & ROIC</div><div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">ROIC: {res.get("roic", 0.0)*100:.1f}%</div></div>', unsafe_allow_html=True)
            with p_c3:
                p3 = res.get("p3_discipline", 0.0)
                st.markdown(f'<div class="metric-card"><div class="metric-value">{p3:.1f} / 1.5</div><div class="metric-label">Pillar 3: Discipline</div><div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">Share Dilution: {res.get("share_count_change_pct", 0.0):+.1f}%</div></div>', unsafe_allow_html=True)
            with p_c4:
                p4 = res.get("p4_valuation", 0.0)
                st.markdown(f'<div class="metric-card"><div class="metric-value">{p4:.1f} / 2.5</div><div class="metric-label">Pillar 4: FCF Yield</div><div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">Yield: {res.get("fcf_yield", 0.0)*100:.1f}%</div></div>', unsafe_allow_html=True)
            with p_c5:
                p5 = res.get("p5_relative", 0.0)
                st.markdown(f'<div class="metric-card"><div class="metric-value">{p5:.1f} / 1.5</div><div class="metric-label">Pillar 5: Relative</div><div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">PEG: {res.get("peg_ratio", 0.0) or "N/A"}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Strengths vs Red Flags
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.markdown("#### **Institutional Strengths**")
                strengths = res.get("strengths", [])
                if strengths:
                    for s in strengths:
                        st.markdown(f"✔ **{s}**")
                else:
                    st.write("No major high-conviction strengths identified.")

            with f_col2:
                st.markdown("#### **Forensic Red Flags & Risks**")
                red_flags = res.get("red_flags", [])
                if red_flags:
                    for rf in red_flags:
                        st.markdown(f"⚠ <span style='color:#f87171;'>{rf}</span>", unsafe_allow_html=True)
                else:
                    st.write("✔ No critical red flags detected.")

            # Data Confidence Drawer
            with st.expander("📊 Audit Verification & Data Lineage"):
                st.write(f"• **Data Confidence Ratio:** {res.get('data_confidence_ratio', 0.0)*100:.1f}% ({res.get('data_extractions_ok', 0)} of {res.get('data_extractions_total', 0)} datapoints validated)")
                st.write(f"• **Cost of Capital (WACC):** {res.get('dynamic_wacc', 0.0)*100:.2f}% | **Economic Spread:** {res.get('economic_spread', 0.0)*100:+.2f}%")
                st.write(f"• **Revenue CAGR:** {res.get('rev_cagr', 0.0)*100:+.2f}% ({res.get('rev_cagr_years', 0)} years)")
                st.write(f"• **Cumulative 4Y Free Cash Flow:** ${res.get('cumulative_fcf', 0.0)/1e9:,.2f}B")
        else:
            st.error(f"Could not retrieve audit data for symbol: {deep_ticker}. Please verify ticker spelling.")
