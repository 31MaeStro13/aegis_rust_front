# Aegis Wealth Terminal — Phase 1 Methods and Results

**Workstream:** Quantitative Research
**Git branch:** `feature/quant-research`
**Workspace:** `research/`
**Status:** Initial market-data validation and portfolio-level daily price-return VaR/CVaR calculations completed. Additional validation and remaining risk metrics are in progress.

## 1. Objective

Develop reproducible quantitative methods for validating market data, constructing portfolio returns, and calculating portfolio risk metrics.

All financial calculations should be deterministic and reproducible. The methodology must document assumptions, preserve missing observations rather than silently filling them, and distinguish observed market data from synthetic test data and hypothetical stress scenarios.

The implementation follows the project's Zero-Calculation LLM principle: financial calculations belong in deterministic Python or Rust functions, not in language-model-generated arithmetic.

## 2. Market-data source and retrieval

### 2.1 Source and requested window

- **Source:** Official Moscow Exchange Information and Statistical Server (MOEX ISS) API.
- **Requested historical window:** 17 October 2023 to 17 October 2026.
- **Rationale:** Approximately three years of market history, as approved by the project lead.
- **Local cache:** `research/data/cache/`
- **Data format:** CSV.
- **Data retrieval implementation:** `research/src/market_data.py`
- **Download script:** `research/download_moex_history.py`

The retrieved data does not necessarily contain observations for the requested end date. Calculations use actual observed dates and explicitly document each dataset's available period.

### 2.2 Retrieved instruments

The local cache contains historical closing-price series for the following instruments:

| Instrument | Board/market | Observed data period | Notes |
|---|---|---|---|
| SBER | TQBR | 17 Oct 2023–16 Oct 2026 | 765 closing-price observations |
| MCFTR | MOEX index | 17 Oct 2023–16 Oct 2026 | 765 closing-price observations |
| GAZP | TQBR | 2 Oct 2023–16 Oct 2026 | 776 observations |
| LKOH | TQBR | 2 Oct 2023–16 Oct 2026 | 776 observations |
| SU26238RMFS4 | TQOB | 2 Oct 2023–16 Oct 2026 | 776 observations |
| SU29014RMFS6 | TQOB | 2 Oct 2023–25 Mar 2026 | Two closing prices are missing at the end of the series; the last valid close is 23 Mar 2026 |
| LQDT | TQTF | 2 Oct 2023–19 Jun 2026 | 691 observations |
| TGLD | TQTF | 2 Oct 2023–19 Jun 2026 | 691 observations |

The cache also contains an earlier short SBER history file. The three-year `SBER_TQBR_history.csv` series is the appropriate SBER file for the calculations documented here.

### 2.3 Data-quality checks

The market-data retrieval and processing workflow checks for:

- Required date and closing-price fields.
- Invalid or unparseable dates.
- Duplicate dates.
- Non-positive or non-finite closing prices.
- Consistency of the date index.
- Missing observations when series are aligned.
- Missing or invalid values in the resulting daily-return series.

The SBER and MCFTR series each contain 765 closing-price observations, with matching dates and no duplicate dates, missing closing prices, or non-positive closing prices in the inspected cache.

The broader multi-asset price panel covers 776 calendar trading-date rows. It contains missing values because the instruments have different history lengths and the SU29014RMFS6 series has missing closing prices near maturity. These missing values are retained and handled explicitly when constructing return samples.

These checks establish basic data integrity. They do not prove that every market-data issue has been eliminated or that every instrument's price series is suitable for every possible valuation purpose.

## 3. Implemented quantitative methods

### 3.1 Herfindahl–Hirschman Index (HHI)

HHI is calculated as the sum of squared portfolio weights expressed in percentage points:

`HHI = sum(weight_percentage²)`

The project's classification thresholds are:

- **Low concentration:** HHI below 1500.
- **Medium concentration:** HHI from 1500 to below 2500.
- **High concentration:** HHI of 2500 or above.

These thresholds are project-defined and should not be presented as universal standards.

### 3.2 Daily asset returns

Simple daily price returns are calculated as:

`Return(t) = Price(t) / Price(t−1) − 1`

The implementation validates input prices and does not forward-fill missing prices. A return is unavailable when the current or preceding required price is missing or invalid.

These are **price returns**, not total returns. They do not automatically include dividends, bond coupon payments, redemption proceeds, or other cash flows.

### 3.3 Portfolio daily returns

Portfolio returns are calculated as the weighted sum of the constituent assets' daily returns:

`Portfolio return(t) = sum(weight(i) × asset return(i,t))`

Portfolio weights are validated to be finite, non-negative, and to sum to one.

The current implementation applies the supplied weights to each day's returns. This represents a **fixed-weight, daily-rebalanced portfolio**, not a buy-and-hold portfolio whose weights drift as asset prices change.

The primary aligned samples require valid daily returns for all assets in the relevant portfolio. Rows with missing asset returns are excluded rather than silently imputed.

### 3.4 Annualized volatility

Annualized volatility is calculated as the sample standard deviation of daily returns multiplied by the square root of 252:

`Annualized volatility = daily sample standard deviation × sqrt(252)`

The factor 252 is the project's assumed number of trading days per year.

### 3.5 Beta

Beta is calculated as the sample covariance between asset and benchmark daily returns divided by the sample variance of benchmark returns.

Asset and benchmark returns must represent matched observations. The initial reported beta is for SBER relative to MCFTR; it is not a portfolio beta.

### 3.6 Historical Value at Risk (VaR)

Historical VaR estimates a loss threshold from the empirical distribution of observed portfolio daily returns.

For confidence level `c`, the implementation uses the return quantile at probability `1 − c` and reports the corresponding loss as a non-negative fraction:

`Historical VaR(c) = max(0, −quantile(returns, 1 − c))`

The reported values are daily historical estimates based on the available aligned sample.

### 3.7 Historical Expected Shortfall (CVaR)

Historical CVaR, also called Expected Shortfall (ES), measures the average loss in the observed lower-tail returns at the selected confidence level.

The implementation identifies returns at or below the empirical `1 − confidence` quantile and reports the negative of their mean, floored at zero.

Because the sample is finite and observations may not divide evenly into the tail, the empirical tail contains the observations selected by this quantile convention. The result depends on the sample and the implementation's quantile convention.

### 3.8 Parametric VaR and CVaR

The parametric estimates use a normal-distribution assumption for daily portfolio returns.

- **Parametric VaR:** Uses the estimated sample mean and sample standard deviation with the relevant normal quantile.
- **Parametric CVaR:** Uses the normal-distribution expected-shortfall formula based on the same estimated mean and standard deviation.

These estimates depend on the normality assumption. They may not capture heavy tails, skewness, abrupt market moves, or changing market regimes.

All VaR and CVaR values in this memo are daily loss estimates expressed as fractions of portfolio value. They are not guaranteed maximum losses or forecasts of future outcomes.

## 4. Portfolio datasets and assumptions

Two portfolio datasets were constructed from the cached market-price series.

### 4.1 Dataset A

| Asset | Weight |
|---|---:|
| SBER | 45.825% |
| GAZP | 26.040% |
| LKOH | 20.550% |
| RUB cash | 7.585% |
| **Total** | **100.000%** |

The RUB cash component is assigned a zero daily return in this dataset. This is a modeling assumption, not an estimate of the interest earned on cash.

- **Aligned daily-return observations:** 764
- **Observed sample period:** 18 October 2023–16 October 2026
- **Return methodology:** Fixed weights with daily rebalancing
- **Return type:** Daily price returns, with zero return assumed for the cash component

### 4.2 Dataset B

| Asset | Weight |
|---|---:|
| SU26238RMFS4 | 27.010% |
| SU29014RMFS6 | 24.625% |
| LQDT | 18.240% |
| SBER | 15.275% |
| TGLD | 14.850% |
| **Total** | **100.000%** |

- **Aligned daily-return observations:** 617
- **Observed sample period:** 18 October 2023–23 March 2026
- **Return methodology:** Fixed weights with daily rebalancing
- **Return type:** Daily price returns

The sample ends on 23 March 2026 because SU29014RMFS6 has no valid closing-price observations on 24 and 25 March 2026, its maturity-date period. The current calculation does not model bond redemption, coupon cash flows, accrued interest, or the subsequent investment of redemption proceeds.

For the two OFZ instruments, the processing script applies a multiplier of 10 to the source closing-price quote, based on the observed quotation convention and a face value of RUB 1,000. This scaling does not change percentage price returns when applied consistently. The current series remain price-only and should not be interpreted as complete bond total-return series.

The bond maturity and missing-price handling require further documented valuation work before Dataset B can be treated as a complete long-horizon bond portfolio risk model.

## 5. Results

### 5.1 Initial single-instrument results

**Observed period:** 17 October 2023–16 October 2026.

| Metric | Result |
|---|---:|
| SBER annualized volatility | 22.0170% |
| MCFTR annualized volatility | 21.8768% |
| SBER beta versus MCFTR | 0.6134 |
| Matched closing-price observations | 765 |
| Matched daily-return observations | 764 |

These results were calculated from the cached MOEX closing-price series using the implemented Python functions.

SBER's estimated annualized volatility was approximately 22.02%. Its estimated beta relative to MCFTR was 0.6134 over the observed sample. These are historical estimates, not forecasts or guarantees of future risk.

These results describe SBER and the selected benchmark. They must not be represented as complete portfolio-level risk results.

### 5.2 Portfolio VaR and CVaR results

The following results were calculated from the aligned daily portfolio price-return samples.

| Portfolio | Confidence | Observations | Historical VaR | Historical CVaR | Parametric VaR | Parametric CVaR |
|---|---:|---:|---:|---:|---:|---:|
| Dataset A | 95% | 764 | 2.0092% | 2.6629% | 2.1362% | 2.6778% |
| Dataset A | 99% | 764 | 2.9358% | 3.7911% | 3.0195% | 3.4587% |
| Dataset B | 95% | 617 | 0.6272% | 0.8449% | 0.6763% | 0.8562% |
| Dataset B | 99% | 617 | 0.9545% | 1.1281% | 0.9697% | 1.1156% |

**Interpretation:**

- Historical VaR estimates the daily loss threshold from the observed sample.
- CVaR estimates the average loss in the selected lower-tail observations.
- Parametric estimates assume daily returns follow a normal distribution.
- The estimates are sensitive to the selected assets, sample window, missing-data policy, weighting method, and return definition.
- Dataset A and Dataset B should not be compared as if they were measured under identical conditions. They contain different holdings and use different sample periods.
- Dataset B's results do not incorporate the missing bond maturity and redemption cash flows. This is a material limitation for a portfolio containing SU29014RMFS6.

The results are reproducible outputs from the current implementation, but they should remain labeled as **daily price-return estimates under the documented assumptions**.

## 6. Software and testing evidence

The Phase 1 research implementation includes:

- `research/src/risk_metrics.py` — quantitative risk functions, including HHI, returns, volatility, beta, portfolio return calculations, and historical/parametric VaR and CVaR.
- `research/src/market_data.py` — MOEX ISS historical data retrieval and cache validation.
- `research/src/portfolio_returns.py` — closing-price loading, daily asset returns, alignment, weight validation, and portfolio return construction.
- `research/tests/` — automated tests for calculation behavior, input validation, market-data retrieval, and portfolio-return construction.
- `research/phase1_risk_metrics.ipynb` — Phase 1 research notebook.
- `research/download_moex_history.py` — market-history download script.
- `research/build_portfolio_datasets.py` — portfolio price and daily-return dataset construction script.
- `research/data/cache/` — locally cached market history, excluded from Git.
- `research/data/processed/` — locally generated processed datasets and risk summaries.

**Latest recorded automated test result:** 40 tests passed.

Run the test suite from the repository root with:

`python -m pytest research\tests -q`

The market-data cache is excluded from Git so that large downloaded files are not committed. The data retrieval and processing scripts should document how to rebuild these local outputs. Small, approved fixtures should be maintained separately for offline testing.

## 7. Reproducibility and data management

The following practices apply:

1. Use the project repository and branch `feature/quant-research`.
2. Keep the Python virtual environment out of Git.
3. Keep large downloaded market-data cache files out of Git.
4. Record the source, retrieval window, actual observed dates, fields, cleaning checks, and assumptions.
5. Preserve missing observations instead of silently forward-filling prices.
6. Keep small, approved benchmark fixtures in `research/data/benchmarks/` or `research/tests/fixtures/` so automated tests can run offline.
7. Record Python and dependency versions for the final deliverable.
8. Rerun automated tests after code changes and record the result.
9. Distinguish observed market data from synthetic test data and hypothetical stress scenarios.
10. Do not claim independent reproduction until the calculations have been rerun from the documented inputs and code.

The generated files in `research/data/processed/` should be regenerated from the cached inputs when the processing logic changes. Before committing, inspect `git status` to ensure that local cache files, temporary files, and other unintended outputs are not staged.

## 8. Limitations and remaining work

The current work establishes a tested initial portfolio-return and daily VaR/CVaR pipeline. It does not yet constitute a complete production-grade portfolio risk engine.

Remaining work includes:

1. **Portfolio beta:** Calculate and validate beta for the portfolio datasets against MCFTR using explicitly matched dates.
2. **Sortino ratio:** Implement downside deviation and the Sortino ratio with a documented target return and frequency convention.
3. **Bond total returns:** Review bond quotation units, accrued interest, coupons, maturity, redemption, and missing maturity-date prices. Document how bond cash flows should enter portfolio valuation and returns.
4. **Bond analytics:** Implement yield to maturity (YTM) and appropriate duration measures when sufficient instrument terms, cash-flow schedules, and market-price inputs are available. Document whether prices are clean or dirty.
5. **Stress testing:** Validate the project's −15% equity shock and reallocation to OFZ floating-rate bonds. Report the assumptions and distinguish scenario losses from probability-based risk estimates.
6. **Risk-free rate:** The project specification identifies a 19% Central Bank of Russia key rate as a baseline. Confirm the applicable date, currency, and suitability before using it in a Sharpe ratio or other risk-adjusted metric.
7. **Data validation:** Review missing observations, instrument lifecycle events, corporate actions, and the suitability of the selected price series for each portfolio.
8. **Executive report:** Prepare the requested concise executive-report blueprint, including allocation, concentration, risk indicators, stress results, and methodological caveats.
9. **Final reproducibility:** Regenerate processed datasets, rerun the notebook and full test suite, record software versions, and verify the final report against the generated results.
10. **Submission evidence:** Update the progress log and prepare the technical memo and notebook for review before marking the Phase 1 milestone complete.

## 9. Record status and next steps

The initial SBER/MCFTR data checks and single-instrument calculations are documented. Portfolio datasets A and B have been constructed, and historical and normal-parametric daily VaR/CVaR calculations have been implemented and tested.

The next priority is to strengthen the portfolio-level validation: calculate portfolio beta and Sortino, resolve the bond price and maturity cash-flow methodology, validate the stress scenario, and prepare the executive-report blueprint.

Until these items are addressed, present the existing VaR/CVaR outputs as **initial, reproducible daily price-return estimates under explicit assumptions**, not as complete total-return portfolio risk measurements or guaranteed loss limits.
