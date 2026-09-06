# Dividend Fortress: Institutional Dividend Growth & Income Architecture

An autonomous, quantitative dividend safety screening, paper portfolio management, and DRIP compounding framework.

---

## 1. Core Philosophy: Why Most Dividend Strategies Fail

Many retail dividend investors suffer from the **"Yield Trap"**:
1. **Chasing Optical Yields**: Buying 8–12% yields where the company is borrowing debt or issuing equity to pay dividends (Free Cash Flow < Dividends Paid).
2. **The Dividend Cut Wipeout**: When a distressed company slashes or suspends its dividend (e.g. Intel, Walgreens, AT&T), the stock price plunges 30–50%, destroying years of dividend income in days.
3. **Inflation Decay**: A static 3% yield without dividend growth loses purchasing power every year.

### The Dividend Fortress Solution
- **FCF Dividend Payout Ratio ($\le 65\%$)**: Dividends must be covered by real operating free cash flow after CapEx, not GAAP accounting adjustments.
- **The Aristocrat & King Durability**: Prioritizing companies with $25+$ (Aristocrats) or $50+$ (Kings) consecutive years of uninterrupted dividend hikes.
- **The Chowder Rule ($\ge 10-12\%$)**: Total Return potential = $\text{Current Dividend Yield (\%)} + \text{5-Year Dividend CAGR (\%)}$.
- **Automated DRIP Compounding**: Systematically reinvesting dividend payouts into purchasing fractional shares to activate exponential compounding.

---

## 2. Architecture & File Structure

```
/Users/sai/dividend_strategy/
├── dividend_reality_auditor.py    # Single-ticker institutional dividend auditor (0-100 Safety Score)
├── dividend_screener.py          # Multi-threaded universe screener (60+ Aristocrats, Kings, REITs)
├── dividend_portfolio_agent.py   # Persistent paper trading agent, PADI, YOC, and monthly income calendar
├── dividend_backtester.py        # 5-year point-in-time DRIP compounding vs SCHD vs SPY backtester
├── dividend_portfolio.json       # Persistent live JSON ledger tracking fractional shares and cash flow
└── README.md                     # Documentation and operations manual
```

---

## 3. Institutional Safety Tiers (0–100 Scale)

| Score Range | Tier Classification | Institutional Description |
|:---:|:---|:---|
| **85 – 100** | `DIVIDEND_FORTRESS` | Pristine balance sheet, FCF payout $<50\%$, 10+ yr streak, near-zero cut risk. |
| **70 – 84** | `SAFE_COMPOUNDER` | Reliable coverage ($<65\%$), consistent dividend hikes across recessions. |
| **50 – 69** | `MODERATE_RISK` | Elevated payout ratio ($65-85\%$), cyclical exposure, or slowing growth. |
| **< 50** | `YIELD_TRAP` | Deficient FCF, debt-funded dividend, recent cut detected, or high risk of slash. |

---

## 4. Quick Start Commands

### 1. Audit Any Single Dividend Stock
Audit dividend coverage, payout frequency, 5Y CAGR, and detect any dividend cut in seconds:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_reality_auditor.py JNJ
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_reality_auditor.py O
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_reality_auditor.py INTC
```

### 2. Scan the Dividend Universe
Run high-speed concurrent audit across 60+ Aristocrats, Kings, and Blue Chips:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_screener.py --workers 16
```
*Optional filters:*
```bash
# Filter for yield >= 3.0%
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_screener.py --min-yield 3.0

# Filter exclusively for Dividend Aristocrats and Kings
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_screener.py --aristocrats
```

### 3. Manage Paper Portfolio & Income Calendar
View active positions, Projected Annual Dividend Income (PADI), Yield on Cost (YOC), and the 12-month calendar:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_portfolio_agent.py --status
```

Rebalance / construct a fresh $1,000 Fortress portfolio from current top qualifiers:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_portfolio_agent.py --rebalance --capital 1000
```

Simulate receiving one quarter of dividends with automatic DRIP reinvestment:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_portfolio_agent.py --drip
```

### 4. Run Historical 5-Year Backtest
Compare DRIP compounding vs cash accumulation vs S&P 500 (`SPY`) and Schwab Dividend ETF (`SCHD`):
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/dividend_strategy/dividend_backtester.py --capital 1000
```

---

## 5. Current Fortress Portfolio Allocation ($1,000 Capital)

| Ticker | Company | Sector | Cost Basis | Yield | YOC | Annual Income | Safety Score | Streak |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **O** | Realty Income Corp | Real Estate | $61.25 | 5.31% | 5.31% | $5.31/yr | **91.0/100** | 29y [Aristocrat] |
| **CMCSA** | Comcast Corporation | Comm. Services | $26.49 | 4.98% | 4.98% | $4.98/yr | **86.0/100** | 23y |
| **ZTS** | Zoetis Inc. | Healthcare | $75.81 | 2.80% | 2.80% | $2.80/yr | **87.0/100** | 12y (+20.1% CAGR) |
| **PLD** | Prologis, Inc. | Real Estate | $137.34 | 3.12% | 3.12% | $2.49/yr | **88.0/100** | 16y (+11.7% CAGR) |
| **ADM** | Archer-Daniels-Midland | Consumer Def. | $84.61 | 2.46% | 2.46% | $2.46/yr | **85.0/100** | 27y [Aristocrat] |
| **AFL** | AFLAC Incorporated | Financial Services | $117.21 | 2.08% | 2.08% | $2.08/yr | **92.0/100** | 41y [Aristocrat] |
| **PH** | Parker-Hannifin | Industrials | $962.59 | 0.83% | 0.83% | $0.83/yr | **100.0/100** | 50y [King] |
| **FDX** | FedEx Corporation | Industrials | $322.52 | 1.51% | 1.51% | $0.76/yr | **91.0/100** | 23y (+17.1% CAGR) |
| **GWW** | W.W. Grainger | Industrials | $1,324.49 | 0.75% | 0.75% | $0.75/yr | **96.0/100** | 50y [King] |
| **MSFT** | Microsoft Corporation | Technology | $499.70 | 0.73% | 0.73% | $0.73/yr | **90.0/100** | 20y (+10.2% CAGR) |
| **CASH** | Uninvested Dry Powder | Cash Reserve | — | — | — | — | — | **$70.00 (7.0%)** |

---

## 6. Backtest Verification (2021 – 2026)

- **Dividend Fortress (WITH DRIP)**: **+112.29% Total Return (14.24% CAGR)**
- **Schwab US Dividend Equity ETF (SCHD)**: **+100.81% Total Return (13.12% CAGR)**
- **S&P 500 Total Return (SPY)**: **+124.05% Total Return (15.34% CAGR)**
- **Max Drawdown**: **-20.74%** (Fortress) vs **-24.50%** (SPY) — significantly superior capital preservation.
