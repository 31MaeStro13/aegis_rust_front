**# Aegis Wealth Terminal — Phase 1 Methods and Results**



**\*\*Workstream:\*\* Quantitative Research**  

**\*\*Git branch:\*\* `feature/quant-research`**  

**\*\*Workspace:\*\* `research/`**  

**\*\*Status:\*\* Market-data retrieval and initial market-risk calculations completed, portfolio-level risk analysis in progress.**



**## 1. Objective**



**Develop reproducible quantitative methods for validating portfolio data and calculating financial risk metrics. Keep calculations deterministic, document assumptions, and distinguish observed market data from synthetic tests and hypothetical stress scenarios.**



**## 2. Approved market-data methodology**



**- \*\*Source:\*\* Official MOEX ISS API.**

**- \*\*Historical window requested:\*\* 17 October 2023 to 17 October 2026.**

**- \*\*Window rationale:\*\* Three years, approximately 750 trading days, as approved by the project lead.**

**- \*\*Retrieved instruments:\*\* SBER, board TQBR; MOEX MCFTR benchmark index.**

**- \*\*Local cache directory:\*\* `research/data/cache/`**

**- \*\*Cached files:\*\***

&#x20; **- `SBER\_TQBR\_history.csv`**

&#x20; **- `MCFTR\_history.csv`**

**- \*\*Returned observation period:\*\* 17 October 2023 to 16 October 2026.**

**- \*\*Retrieved observations:\*\* 765 closing-price records per series.**

**- \*\*Return observations:\*\* 764 per series.**



**The requested end date is not itself present in the returned data. Used the actual observed date range in calculations and reports.**



**## 3. Data-quality checks performed**



**The following checks were performed on both cached CSV files:**



**- Confirmed the expected date and closing price fields were present.**

**- Checked missing dates and closing prices.**

**- Checked duplicate trading dates.**

**- Checked for non-positive closing prices.**

**- Compared the trading dates in the SBER and MCFTR datasets.**



**\*\*Observed results:\*\***



**| Check | SBER | MCFTR |**

**|---|---:|---:|**

**| Price observations | 765 | 765 |**

**| Missing dates/prices | 0 | 0 |**

**| Duplicate dates | 0 | 0 |**

**| Non-positive closing prices | 0 | 0 |**



**All 765 dates matched between the two datasets.**



**These checks establish basic data integrity. They do not independently establish that the data is free from every market-data issue or that the benchmark is appropriate for every portfolio metric.**



**## 4. Implemented quantitative methods**



**### 4.1 Herfindahl–Hirschman Index (HHI)**



**The existing function `calculate\_hhi()` calculates concentration from percentage weights:**



**HHI = sum of squared percentage weights.**



**The function `classify\_hhi()` uses the project's specified thresholds:**



**- Below 1500: Low**

**- 1500 to below 2500: Medium**

**- 2500 or above: High**



**These are project-defined thresholds and should not be presented as universal standards.**



**### 4.2 Daily returns**



**Simple daily returns are calculated from consecutive closing prices:**



**Return(t) = Price(t) / Price(t−1) − 1.**



**The function validates the input and rejects non-positive or non-finite prices.**



**### 4.3 Annualized volatility**



**Annualized volatility is calculated as the sample standard deviation of daily returns multiplied by the square root of 252.**



**This assumes 252 trading days per year as the project's annualization convention.**



**### 4.4 Beta**



**Beta is calculated as the sample covariance between asset and benchmark daily returns divided by the sample variance of benchmark returns.**



**The asset and benchmark returns must have equal lengths and represent matched observations.**



**## 5. Initial observed results**



**\*\*Period:\*\* 17 October 2023 to 16 October 2026.**



**| Metric | Result |**

**|---|---:|**

**| SBER annualized volatility | 22.0170% |**

**| MCFTR annualized volatility | 21.8768% |**

**| SBER beta versus MCFTR | 0.6134 |**

**| Matched price observations | 765 |**

**| Matched daily return observations | 764 |**



**These results were calculated from the cached MOEX closing-price series using the implemented Python functions.**



**\*\*Interpretation:\*\* SBER's estimated annualized volatility was approximately 22.02%. Its estimated beta relative to MCFTR was 0.6134 over this sample. These are historical estimates, not forecasts or guarantees of future risk.**



**The calculations describe SBER and the selected benchmark. They must not be represented as complete portfolio-level risk results.**



**## 6. Software and testing evidence**



**- Reusable calculation module: `research/src/risk\_metrics.py`**

**- MOEX data retrieval module: `research/src/market\_data.py`**

**- Automated tests: `research/tests/`**

**- Phase 1 notebook: `research/phase1\_risk\_metrics.ipynb`**

**- Market-data cache: `research/data/cache/`**



**\*\*Latest recorded test result:\*\* 20 tests passed in 1.55 seconds.**



**The tests cover HHI, daily returns, annualized volatility, beta, and invalid input conditions.**



**## 7. Reproducibility and data management**



**- Use the project repository and branch `feature/quant-research`.**

**- Keep the Python virtual environment out of Git.**

**- Large downloaded market-data cache files are excluded from Git.**

**- Record the data source, retrieval date, requested window, observed window, fields, cleaning checks, and calculation assumptions.**

**- Keep small, approved benchmark fixtures in `research/data/benchmarks/` or `research/tests/fixtures/` so tests can run offline.**

**- Record Python and dependency versions when preparing the final deliverable.**

**- Rerun automated tests after changes and record the results.**

**- Do not describe synthetic test data as actual market performance.**

**- Do not claim a calculation is independently reproduced until it has been rerun from the documented inputs and code.**



**## 8. Outstanding work**



**1. Validate the historical window and benchmark methodology for all portfolio instruments.**

**2. Establish portfolio holdings and obtain appropriate historical prices for the required assets.**

**3. Align the asset price series and document missing observations and corporate-action assumptions.**

**4. Construct and validate portfolio daily returns using an explicit weighting and rebalancing methodology.**

**5. Implement historical VaR and Expected Shortfall (CVaR) at 95% and 99%, with documented tail conventions.**

**6. Implement and validate any remaining required metrics, including Sortino and bond duration/YTM where suitable data is available.**

**7. Prepare the technical memo and executive-report blueprint.**

**8. Rerun the complete test suite and record the final evidence before submitting the Phase 1 milestone.**



**## 9. Next decision**



**Do not report SBER volatility or beta as portfolio-level metrics. Proceed to portfolio return construction and data validation before publishing portfolio VaR/CVaR results.**



**\*\*Record status:\*\* Initial methods and results documented; portfolio-level analysis remains incomplete.**

