# Phase 1 Progress Log

## 18 October 2026 — Portfolio Returns and Initial Risk Metrics

### Completed

- Corrected the MOEX ISS request to retrieve historical data and pagination metadata.
- Downloaded and cached historical closing-price data from the official MOEX ISS API.
- Implemented historical market-data retrieval and validation.
- Implemented daily returns, annualized volatility, beta, and portfolio return calculations.
- Constructed two benchmark portfolio datasets using documented fixed weights and aligned daily price returns.
- Implemented historical and normal-parametric VaR and CVaR calculations at 95% and 99% confidence levels.
- Added automated tests for market-data handling, portfolio return construction, risk metrics, and input validation.
- Updated the Phase 1 methods and results memo with data coverage, portfolio results, methodology, assumptions, and limitations.
- Verified that the current automated test suite passes: **40 tests passed**.

### Initial Results

**SBER and MCFTR benchmark analysis**
- SBER annualized volatility: 22.0170%.
- MCFTR annualized volatility: 21.8768%.
- SBER beta relative to MCFTR: 0.6134.
- Matched closing-price observations: 765.
- Matched daily-return observations: 764.

**Portfolio datasets**
- Dataset A: 764 daily portfolio-return observations, from 18 October 2023 to 16 October 2026.
- Dataset B: 617 daily portfolio-return observations, from 18 October 2023 to 23 March 2026.
- Historical and normal-parametric VaR/CVaR estimates were calculated at 95% and 99% confidence levels.

These are initial daily price-return estimates. They are not guaranteed loss limits or complete total-return portfolio risk measurements.

### Outstanding Work

- Calculate and validate portfolio beta against MCFTR.
- Implement and test the Sortino ratio and downside deviation.
- Review bond quotation units, accrued interest, coupon payments, maturity, and redemption cash flows.
- Implement bond yield-to-maturity and suitable duration measures when sufficient inputs are available.
- Validate the specified −15% equity stress scenario and OFZ floating-rate bond reallocation.
- Confirm the applicable risk-free rate and its suitability for the chosen currency and observation period.
- Complete the executive-report blueprint.
- Rerun the notebook and processing scripts from documented inputs, verify the generated results, and record dependency versions.
- Update the final deliverables and obtain review before declaring Phase 1 complete.

### Evidence

- `research/src/market_data.py`
- `research/src/risk_metrics.py`
- `research/src/portfolio_returns.py`
- `research/tests/`
- `research/phase1_risk_metrics.ipynb`
- `research/download_moex_history.py`
- `research/build_portfolio_datasets.py`
- `research/memo/PHASE1_METHODS_AND_RESULTS.md`
- Local market-data cache: `research/data/cache/` (excluded from Git)
- Locally generated outputs: `research/data/processed/`

### Test Evidence

Command: `python -m pytest research\tests -q`

Latest result: **40 passed**.

### Important Limitations

Dataset B ends on 23 March 2026 because the SU29014RMFS6 bond's maturity and redemption cash flows have not yet been modeled. The current portfolio results use fixed weights applied to daily price returns and exclude bond coupon and redemption cash flows. These limitations must be resolved or clearly documented before the analysis is presented as a complete portfolio total-return risk assessment.