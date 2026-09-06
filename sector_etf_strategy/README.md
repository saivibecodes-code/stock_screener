# Sector ETF Rotation: Macro-Regime & Relative Momentum Framework

An autonomous, quantitative sector ETF analysis, macro business cycle diagnosis, paper portfolio management, and dual-momentum rotation framework.

---

## 1. Core Philosophy: Why Sector ETF Rotation Works

The stock market does not move as a monolith. Capital constantly rotates between sectors depending on **economic growth**, **interest rates**, **inflation**, and **liquidity regimes**:
- **Early-Cycle (Recovery / Expansion)**: Financials (`XLF`), Consumer Discretionary (`XLY`), Industrials (`XLI`), Real Estate (`XLRE`).
- **Mid-Cycle (Peak Growth / AI Boom)**: Technology (`XLK`), Communication Services (`XLC`), Industrials (`XLI`).
- **Late-Cycle (Inflation & Energy Shocks)**: Energy (`XLE`), Materials (`XLB`), Healthcare (`XLV`).
- **Recession / Contraction (Flight-to-Safety)**: Utilities (`XLU`), Consumer Staples (`XLP`), Healthcare (`XLV`), Cash.

By systematically identifying leading sectors and rotating out of lagging/distressed sectors, institutional investors achieve **superior risk-adjusted returns (higher Sharpe ratio)** and **significantly reduced drawdowns**.

---

## 2. Architecture & File Structure

```
/Users/sai/sector_etf_strategy/
├── sector_etf_analyzer.py        # Single ETF auditor (Momentum vs SPY, 50d/200d SMA, RSI, Concentration, RRG)
├── sector_etf_screener.py        # High-speed scanner across 11 GICS sectors + Thematics with Macro Diagnosis
├── sector_rotation_portfolio.py  # Persistent paper trading agent with SPY 200-SMA regime safety switch
├── sector_rotation_backtester.py # 5-Year historical backtest vs SPY & Equal-Weight S&P (RSP)
├── sector_portfolio.json         # Persistent live JSON ledger tracking fractional shares and cash flow
└── README.md                     # Comprehensive operations manual & mathematical formulation
```

---

## 3. The 4 Relative Rotation Graph (RRG) Quadrants

| Quadrant | RS-Ratio & RS-Momentum | Institutional Interpretation & Action |
|:---:|:---:|:---|
| **LEADING** | High RS / Accelerating Mom | Outperforming S&P 500 with increasing strength. **Strong Overweight**. |
| **WEAKENING** | High RS / Decelerating Mom | Still outperforming, but losing relative velocity. **Overweight / Take Profits**. |
| **LAGGING** | Low RS / Decelerating Mom | Underperforming S&P 500 with downward momentum. **Underweight / Avoid**. |
| **IMPROVING** | Low RS / Accelerating Mom | Turning around from oversold levels. **Accumulation Watchlist**. |

---

## 4. Quick Start Commands

### 1. Audit Any Single Sector or Thematic ETF
Analyze relative momentum spreads vs SPY, moving averages, 14-day RSI, and top component holdings:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_etf_analyzer.py XLK
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_etf_analyzer.py XLE
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_etf_analyzer.py SMH
```

### 2. Scan the Full Sector Universe
Run high-speed concurrent audit across the 11 GICS sector SPDRs and top thematic ETFs in 3 seconds:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_etf_screener.py --workers 16
```

### 3. Manage Paper Portfolio & Tactical Rebalancing
Check active portfolio status and market regime:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_rotation_portfolio.py --status
```

Rebalance the $1,000 portfolio into the current top leading sectors:
```bash
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_rotation_portfolio.py --rebalance --capital 1000
```

### 4. Run Historical Backtest
Compare quantitative sector rotation against S&P 500 (`SPY`) and Equal-Weight S&P (`RSP`):
```bash
# Monthly rebalancing
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_rotation_backtester.py --capital 1000 --freq M

# Quarterly rebalancing
/Users/sai/seeking_alpha_scraper/venv/bin/python3 /Users/sai/sector_etf_strategy/sector_rotation_backtester.py --capital 1000 --freq Q
```

---

## 5. Current Sector Paper Portfolio ($1,000 Capital)

| ETF | Sector / Theme | Cost Basis | Market Val | Weight | Score | RRG State | Strategic Role |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **XLK** | Technology | $187.28 | $237.50 | 23.7% | **86.3** | `LEADING` | Offensive Leadership |
| **XLE** | Energy | $64.06 | $237.50 | 23.8% | **77.0** | `WEAKENING` | Offensive Leadership (+11.8% 1M Spread) |
| **XLV** | Healthcare | $171.45 | $237.50 | 23.7% | **73.5** | `WEAKENING` | Offensive Leadership (+8.4% 3M Spread) |
| **XBI** | Biotechnology | $163.81 | $237.50 | 23.7% | **97.0** | `WEAKENING` | Thematic Alpha (+23.2% 3M Spread) |
| **CASH** | Dry Powder Reserve | — | **$50.00** | **5.0%** | — | — | Liquidity Buffer |

- **Market Regime**: `BULL_MARKET` (`SPY` is +8.50% above its 200-day SMA).
- **Inferred Macro Business Cycle**: `Late-Cycle (Inflation / Commodity Outperformance)`.

---

## 6. Backtest Highlights (2021 – 2026)

- **Tactical Sector Rotation (Monthly)**: **+104.89% Total Return (13.53% CAGR)**
- **Sharpe Ratio**: **`0.96` vs SPY's `0.94`** (Higher risk-adjusted return than the market index).
- **Max Drawdown**: **`-15.75%` vs SPY's `-24.50%`** (35% reduction in downside market crash risk).
