
"""Build reproducible price-return datasets for Aegis Phase 1.

These outputs use fixed portfolio weights (daily rebalancing).
Bond results are price-only, not total returns.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "research" / "data" / "cache"
OUTPUT = ROOT / "research" / "data" / "processed"

sys.path.insert(0, str(ROOT))

from research.src.portfolio_returns import (  # noqa: E402
    load_close_series,
    build_asset_returns,
    align_asset_returns,
    calculate_portfolio_returns,
)
from research.src.risk_metrics import (  # noqa: E402
    historical_var,
    historical_cvar,
    parametric_var,
    parametric_cvar,
)

# Project onboarding benchmark weights. Cash has a constant zero price return.
DATASET_A_WEIGHTS = {
    "SBER": 0.45825,
    "GAZP": 0.26040,
    "LKOH": 0.20550,
    "RUB": 0.07585,
}

DATASET_B_WEIGHTS = {
    "SU26238RMFS4": 0.27010,
    "SU29014RMFS6": 0.24625,
    "LQDT": 0.18240,
    "SBER": 0.15275,
    "TGLD": 0.14850,
}

# Source close values for these OFZ bonds are quoted in percentage points
# of a 1,000 RUB face value: 1 quote point = 10 RUB.
BOND_PRICE_MULTIPLIER = 10.0


def load_security_prices() -> pd.DataFrame:
    """Load the six benchmark securities and standardize their price units."""
    specifications = {
        "SBER": ("SBER_TQBR_history.csv", 1.0),
        "GAZP": ("GAZP_TQBR_history.csv", 1.0),
        "LKOH": ("LKOH_TQBR_history.csv", 1.0),
        "SU26238RMFS4": (
            "SU26238RMFS4_TQOB_history.csv",
            BOND_PRICE_MULTIPLIER,
        ),
        "SU29014RMFS6": (
            "SU29014RMFS6_TQOB_history.csv",
            BOND_PRICE_MULTIPLIER,
        ),
        "LQDT": ("LQDT_TQTF_history.csv", 1.0),
        "TGLD": ("TGLD_TQTF_history.csv", 1.0),
    }

    series = []
    for security, (filename, multiplier) in specifications.items():
        path = CACHE / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing cached history: {path}")

        prices = load_close_series(
            str(path),
            security=security,
            price_multiplier=multiplier,
        )
        series.append(prices)

    # Outer alignment preserves missing observations instead of filling them.
    panel = pd.concat(series, axis=1, join="outer", sort=True).sort_index()
    panel.index.name = "TRADEDATE"
    return panel


def make_portfolio(
    asset_returns: pd.DataFrame,
    weights: dict[str, float],
    *,
    cash_asset: str | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Calculate portfolio returns on dates with valid observations for all assets."""
    panel = asset_returns.copy()

    if cash_asset is not None:
        panel[cash_asset] = 0.0

    assets = list(weights)
    missing = set(assets).difference(panel.columns)
    if missing:
        raise ValueError(f"Missing return series for: {sorted(missing)}")

    aligned = align_asset_returns(panel[assets], require_all_assets=True)
    portfolio = calculate_portfolio_returns(aligned, weights)
    return aligned, portfolio


def risk_summary(
    portfolio: pd.Series,
    *,
    portfolio_name: str,
) -> list[dict]:
    """Calculate historical and normal-parametric VaR/CVaR at 95% and 99%."""
    returns = portfolio.to_numpy(dtype=float)

    rows = []
    for confidence in (0.95, 0.99):
        rows.append(
            {
                "portfolio": portfolio_name,
                "confidence_level": confidence,
                "observations": len(returns),
                "start_date": portfolio.index.min().date().isoformat(),
                "end_date": portfolio.index.max().date().isoformat(),
                "historical_var": historical_var(returns, confidence),
                "historical_cvar": historical_cvar(returns, confidence),
                "parametric_var": parametric_var(returns, confidence),
                "parametric_cvar": parametric_cvar(returns, confidence),
                "return_type": "daily price return",
                "weighting": "fixed weights; daily rebalancing",
            }
        )
    return rows


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    prices = load_security_prices()
    prices.to_csv(OUTPUT / "normalized_prices.csv", index_label="TRADEDATE")

    asset_returns = build_asset_returns(prices)
    asset_returns.to_csv(
        OUTPUT / "asset_daily_returns.csv",
        index_label="TRADEDATE",
    )

    # Dataset A: shares plus RUB cash. Cash is assumed to earn zero daily return.
    returns_a, portfolio_a = make_portfolio(
        asset_returns,
        DATASET_A_WEIGHTS,
        cash_asset="RUB",
    )
    portfolio_a.to_frame().to_csv(
        OUTPUT / "dataset_a_portfolio_returns.csv",
        index_label="TRADEDATE",
    )

    # Dataset B: the common price-history window ends when the maturing
    # OFZ's valid market-close history ends. No maturity cash flow is modeled.
    returns_b, portfolio_b = make_portfolio(
        asset_returns,
        DATASET_B_WEIGHTS,
    )
    portfolio_b.to_frame().to_csv(
        OUTPUT / "dataset_b_portfolio_returns.csv",
        index_label="TRADEDATE",
    )

    summaries = (
        risk_summary(portfolio_a, portfolio_name="Dataset A")
        + risk_summary(portfolio_b, portfolio_name="Dataset B")
    )
    pd.DataFrame(summaries).to_csv(
        OUTPUT / "portfolio_risk_summary.csv",
        index=False,
    )

    print("Portfolio dataset generation completed.")
    print(f"Output directory: {OUTPUT}")
    print(f"Normalized price rows: {len(prices)}")
    print(f"Asset return rows: {len(asset_returns)}")
    print(
        "Dataset A:",
        len(portfolio_a),
        "observations from",
        portfolio_a.index.min().date(),
        "to",
        portfolio_a.index.max().date(),
    )
    print(
        "Dataset B:",
        len(portfolio_b),
        "observations from",
        portfolio_b.index.min().date(),
        "to",
        portfolio_b.index.max().date(),
    )
    print("\nRisk summary:")
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == "__main__":
    main()
