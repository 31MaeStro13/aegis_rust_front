
"""Portfolio return construction and data-quality checks.

Portfolio returns use fixed starting weights, which is equivalent to
daily rebalancing. These are price returns, not total returns.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


DATE_COLUMN = "TRADEDATE"
CLOSE_COLUMN = "CLOSE"


def load_close_series(
    path: str,
    *,
    security: str,
    price_multiplier: float = 1.0,
) -> pd.Series:
    """Load one cached MOEX history as a validated close-price series.

    Missing or invalid closes remain missing; they are never forward-filled.
    price_multiplier converts the source price into the chosen common unit.
    """
    frame = pd.read_csv(path)

    required = {DATE_COLUMN, CLOSE_COLUMN}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if not np.isfinite(price_multiplier) or price_multiplier <= 0:
        raise ValueError("price_multiplier must be finite and positive")

    dates = pd.to_datetime(frame[DATE_COLUMN], errors="coerce")
    closes = pd.to_numeric(frame[CLOSE_COLUMN], errors="coerce")

    if dates.isna().any():
        raise ValueError("History contains invalid trade dates")

    if dates.duplicated().any():
        raise ValueError("History contains duplicate trade dates")

    if not dates.is_monotonic_increasing:
        raise ValueError("History must be sorted by trade date")

    # Keep missing and non-positive closes as missing observations.
    closes = closes.where(np.isfinite(closes) & (closes > 0))
    closes = closes * price_multiplier

    result = pd.Series(closes.to_numpy(), index=dates, name=security)
    result.index.name = DATE_COLUMN
    return result


def build_asset_returns(
    prices: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate one-period price returns without bridging missing prices.

    If today's or the previous row's price is missing, the return is missing.
    Rows must represent the aligned trading-date calendar.
    """
    if prices.empty:
        raise ValueError("prices must not be empty")

    if prices.index.has_duplicates:
        raise ValueError("prices index contains duplicate dates")

    if not prices.index.is_monotonic_increasing:
        raise ValueError("prices must be sorted by date")

    numeric = prices.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.where(np.isfinite(numeric) & (numeric > 0))

    # pct_change(fill_method=None) prevents pandas from filling missing prices.
    returns = numeric.pct_change(fill_method=None)
    return returns.replace([np.inf, -np.inf], np.nan)


def align_asset_returns(
    returns: pd.DataFrame,
    *,
    require_all_assets: bool = True,
) -> pd.DataFrame:
    """Align returns by exact date and remove unusable observations."""
    if returns.empty:
        raise ValueError("returns must not be empty")

    if returns.index.has_duplicates:
        raise ValueError("returns index contains duplicate dates")

    if not returns.index.is_monotonic_increasing:
        raise ValueError("returns must be sorted by date")

    numeric = returns.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)

    if require_all_assets:
        return numeric.dropna(axis=0, how="any")

    return numeric.dropna(axis=0, how="all")


def validate_weights(
    weights: Mapping[str, float],
    assets: Sequence[str],
) -> pd.Series:
    """Validate and order non-negative portfolio weights summing to one."""
    if not assets:
        raise ValueError("At least one asset is required")

    if len(set(assets)) != len(assets):
        raise ValueError("Asset names must be unique")

    if set(weights) != set(assets):
        raise ValueError("Weights must match the asset names exactly")

    result = pd.Series(
        [weights[asset] for asset in assets],
        index=list(assets),
        dtype=float,
    )

    values = result.to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("Weights must be finite")

    if (values < 0).any():
        raise ValueError("Weights must be non-negative")

    if not np.isclose(values.sum(), 1.0, atol=1e-8):
        raise ValueError("Weights must sum to 1")

    return result


def calculate_portfolio_returns(
    asset_returns: pd.DataFrame,
    weights: Mapping[str, float],
) -> pd.Series:
    """Calculate daily-rebalanced portfolio returns from aligned asset returns."""
    if asset_returns.empty:
        raise ValueError("asset_returns must not be empty")

    if asset_returns.isna().any().any():
        raise ValueError(
            "Align and remove missing asset returns before portfolio calculation"
        )

    values = asset_returns.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Asset returns must be finite")

    ordered_weights = validate_weights(weights, list(asset_returns.columns))

    portfolio = asset_returns @ ordered_weights
    portfolio.name = "portfolio_return"
    return portfolio
