**# Phase 1 Progress Log**



**## 17 October 2026 - Market-data and initial risk-metric milestone**



**\*\*Completed\*\***

**- Corrected the MOEX ISS request so both history and pagination-cursor sections are returned.**

**- Downloaded SBER/TQBR and MCFTR closing-price histories through the official MOEX ISS API.**

**- Saved the CSV files under `research/data/cache/`.**

**- Verified 765 observations per dataset, 765 matching dates, no missing dates/prices, no duplicate dates and no non-positive closing prices.**

**- Implemented daily returns, annualized volatility and beta in `research/src/risk\_metrics.py`.**

**- Recorded 20 passing automated tests.**

**- Calculated SBER annualized volatility of 22.0170%, MCFTR annualized volatility of 21.8768%, and SBER beta of 0.6134 over the observed sample.**



**\*\*Outstanding\*\***

**- Construct portfolio-level daily returns.**

**- Validate the portfolio benchmark and historical coverage.**

**- Implement and test historical VaR/CVaR at 95% and 99%.**

**- Complete the remaining Phase 1 metrics and technical memo.**



**\*\*Evidence\*\***

**- `research/src/market\_data.py`**

**- `research/src/risk\_metrics.py`**

**- `research/tests/`**

**- `research/data/cache/SBER\_TQBR\_history.csv` (local, ignored by Git)**

**- `research/data/cache/MCFTR\_history.csv` (local, ignored by Git)**

**- `research/memo/PHASE1\_METHODS\_AND\_RESULTS.md`**



**\*\*Test evidence:\*\* 20 passed in 1.55 seconds.**

