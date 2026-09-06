# 📈 Institutional Reality Screener & Multi-Strategy Quantitative Suite

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An institutional-grade, multi-strategy quantitative equity screening and portfolio management suite. Built to filter through Wall Street hype using forensic cash flow auditing, dynamic hurdle rates, Chowder Rule dividend defense, and tactical sector ETF momentum rotation.

---

## 🏛️ The Three Quantitative Pillars

```
                     ┌───────────────────────────────────────────────────────────┐
                     │     QUANTITATIVE REALITY ALLOCATION ENGINE                │
                     └─────────────────────────────┬─────────────────────────────┘
                                                   │
          ┌────────────────────────────────────────┼────────────────────────────────────────┐
          │                                        │                                        │
          ▼                                        ▼                                        ▼
┌───────────────────────────┐            ┌───────────────────────────┐            ┌───────────────────────────┐
│   PILLAR I: TOP 200       │            │   PILLAR II: DIVIDEND     │            │   PILLAR III: TACTICAL    │
│   REALITY SCREENER        │            │   FORTRESS ENGINE         │            │   SECTOR ETF ROTATION     │
├───────────────────────────┤            ├───────────────────────────┤            ├───────────────────────────┤
│ • Top 200 US Mega-Caps    │            │ • 74 Dividend Stalwarts   │            │ • 11 GICS Sector SPDRs    │
│ • Quality Gate (≥ 6.0/10) │            │ • Aristocrats & Kings     │            │ • Thematic ETFs (SMH, XBI)│
│ • Valuation Gate (≥ 5.0)  │            │ • FCF Payout Ratio ≤ 70%  │            │ • SPY 200-SMA Regime Rule │
│ • Multi-Sector 15-Stock   │            │ • Chowder Rule (Yield+CAGR│            │ • Relative Rotation (RRG) │
│   Paper Model Portfolio   │            │ • 10-Stock DRIP Portfolio │            │ • Tactical Rebalancing    │
└───────────────────────────┘            └───────────────────────────┘            └───────────────────────────┘
```

---

## 🚀 Quick Start (Run Locally)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/<your-username>/stock_screener.git
cd stock_screener
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch the Streamlit Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deploying to Streamlit Community Cloud (1-Click)

1. **Push this repository to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Institutional Reality Screener & Strategy Suite"
   git branch -M main
   git remote add origin https://github.com/<your-username>/stock_screener.git
   git push -u origin main
   ```
2. **Go to [share.streamlit.io](https://share.streamlit.io/)** and sign in with your GitHub account.
3. **Click "Create app"**, select your `stock_screener` repository, branch `main`, and set **Main file path** to:
   ```text
   app.py
   ```
4. **Deploy!** The pre-computed cache files (`.cache_top200.json`, `.cache_dividend.json`, `.cache_sector.json`) ensure your cloud app boots **instantly in sub-seconds** without waiting for network scans.

---

## 🖥️ Web App Features & Tabs

| Tab | Feature Description |
| :--- | :--- |
| **🏆 Top 200 Reality Screener** | Institutional matrix plotting Quality vs Valuation, sector filters, Altman-Z solvency scores, and dual-gate pass/fail classifications. |
| **🛡️ Dividend Fortress** | Interactive Chowder Rule plane (Yield % vs 5Y Dividend CAGR %), dividend safety tiers, payout ratio checks, and cut history alerts. |
| **🌐 Sector ETF Rotation** | Live Market Regime banner (SPY vs 200 SMA), Relative Rotation Graphs (RRG quadrants: Leading, Weakening, Lagging, Improving), and tactical overweight/underweight rankings. |
| **💼 Active Model Portfolios** | Live tracking of all 3 $1,000 model paper trading ledgers with capital distribution donut charts, P&L attribution, and transaction history. |
| **🔍 Single-Stock Deep Dive** | Instant on-demand audit of ANY ticker symbol across 5 forensic accounting pillars (Solvency, Moat, Discipline, Valuation, Momentum). |

---

## 📁 Repository Structure

```
stock_screener/
├── app.py                             # Unified Streamlit Web Dashboard (5 Tabs)
├── requirements.txt                   # Production dependencies
├── .gitignore                         # Git exclusion rules
├── README.md                          # Project documentation & deployment guide
│
├── stock_reality_auditor.py           # v3.1 5-Pillar Institutional Reality Auditor
├── top200_universe_screener.py        # Top 200 Multi-Sector Scanner & Screener
├── top100_universe_screener.py        # Top 100 S&P 500 & Nasdaq-100 Scanner
├── paper_trade_agent.py               # Paper Trading Agent for Top 200 Portfolio
├── paper_portfolio.json               # Persistent Top 200 model portfolio ledger ($1,000)
├── historical_backtest.py             # 5-Year Historical Performance Backtester
├── long_term_20yr_analysis.py         # 20-Year Long-Term Multi-Cycle Analyzer
│
├── dividend_strategy/                 # Pillar II: Dividend Fortress Engine
│   ├── dividend_reality_auditor.py    # Dividend cash flow safety auditor
│   ├── dividend_screener.py           # 74-stock dividend universe scanner
│   ├── dividend_portfolio_agent.py    # Dividend paper portfolio agent with DRIP
│   ├── dividend_backtester.py         # 10-Year DRIP dividend backtester
│   ├── dividend_portfolio.json        # Persistent dividend model portfolio ledger ($1,000)
│   └── README.md                      # Dividend strategy documentation
│
├── sector_etf_strategy/               # Pillar III: Tactical Sector ETF Rotation
│   ├── sector_etf_analyzer.py         # Relative momentum, RSI, RRG & fundamentals
│   ├── sector_etf_screener.py         # 19 Sector & Thematic ETF ranking scanner
│   ├── sector_rotation_portfolio.py   # Regime-driven rebalancer & ledger
│   ├── sector_rotation_backtester.py  # Tactical sector rotation backtester
│   ├── sector_portfolio.json          # Persistent sector ETF model ledger ($1,000)
│   └── README.md                      # Sector rotation strategy documentation
│
├── .cache_top200.json                 # Pre-computed scan of 210 Top US champions
├── .cache_dividend.json               # Pre-computed scan of 74 Dividend stalwarts
└── .cache_sector.json                 # Pre-computed scan of 19 Sector & Thematic ETFs
```

---

## 🛠️ CLI Execution Options

If you prefer running quantitative scans or updating paper ledgers directly from the terminal:

### Run Top 200 Reality Scan:
```bash
python3 top200_universe_screener.py --capital 1000 --sync-paper
```

### Run Dividend Fortress Scan:
```bash
python3 dividend_strategy/dividend_screener.py --min-yield 2.5
python3 dividend_strategy/dividend_portfolio_agent.py --status
```

### Run Sector Rotation Rebalance:
```bash
python3 sector_etf_strategy/sector_rotation_portfolio.py --rebalance --capital 1000
```

### Run Audit on a Single Stock:
```bash
python3 stock_reality_auditor.py AAPL
python3 dividend_strategy/dividend_reality_auditor.py JNJ
python3 sector_etf_strategy/sector_etf_analyzer.py XLK
```

---

## ⚖️ Disclaimer
*This software is intended for research, educational, and paper-trading purposes only. It is not financial or investment advice. Always perform your own due diligence before deploying real capital.*
