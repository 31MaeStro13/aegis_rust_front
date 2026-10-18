# Aegis Wealth Terminal — Quantitative Research

## Purpose

This workspace contains reproducible quantitative research for portfolio
risk analysis and market-data validation.

## Phase 1 scope

- Validate the supplied benchmark portfolios.
- Retrieve historical market data through the official MOEX ISS API.
- Compare portfolio instruments with the MOEX MCFTR benchmark where appropriate.
- Calculate and validate portfolio risk metrics.
- Document assumptions, missing observations, and limitations.
- Produce a technical memo and executive-report blueprint.

## Directory structure

- `src/`: reusable Python modules.
- `tests/`: automated tests and test fixtures.
- `notebooks/`: additional exploratory notebooks.
- `data/benchmarks/`: small, approved benchmark datasets.
- `data/cache/`: local historical market-data cache.
- `memo/`: technical documentation and reports.

The Phase 1 notebook is currently maintained at
`research/phase1_risk_metrics.ipynb`.

## Data management

Large downloaded market-data files in `data/cache/` are excluded from Git.
Small benchmark fixtures may be committed when they are appropriate to share.

Record the source, retrieval date, date range, relevant fields, and cleaning
assumptions for historical data. Do not commit credentials or confidential data.

## Reproducibility

Use the project's documented Python environment and run the automated tests
before submitting changes. Test fixtures should allow key calculations to be
verified without downloading live market data.

## Methodology

Do not report synthetic returns as actual market performance. Clearly
distinguish observed market data, assumptions, stress scenarios, and synthetic
test data.
