
import numpy as np
import pandas as pd
import pytest

from research.src.portfolio_returns import (
    align_asset_returns,
    build_asset_returns,
    calculate_portfolio_returns,
    validate_weights,
)


def test_build_asset_returns_does_not_fill_missing_prices():
    prices = pd.DataFrame(
        {"A": [100.0, np.nan, 110.0, 121.0]},
        index=pd.to_datetime(
            ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
        ),
    )

    returns = build_asset_returns(prices)

    assert np.isnan(returns["A"].iloc[0])
    assert np.isnan(returns["A"].iloc[1])
    assert np.isnan(returns["A"].iloc[2])
    assert returns["A"].iloc[3] == pytest.approx(0.10)


def test_align_asset_returns_requires_all_assets_by_default():
    returns = pd.DataFrame(
        {
            "A": [0.01, 0.02, np.nan],
            "B": [0.03, np.nan, 0.04],
        },
        index=pd.date_range("2026-01-01", periods=3),
    )

    aligned = align_asset_returns(returns)

    assert len(aligned) == 1
    assert aligned.iloc[0].tolist() == [0.01, 0.03]


def test_validate_weights_preserves_asset_order():
    weights = validate_weights(
        {"B": 0.4, "A": 0.6},
        ["A", "B"],
    )

    assert weights.index.tolist() == ["A", "B"]
    assert weights.tolist() == [0.6, 0.4]


def test_validate_weights_rejects_weights_not_summing_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        validate_weights({"A": 0.6, "B": 0.3}, ["A", "B"])


def test_calculate_portfolio_returns():
    returns = pd.DataFrame(
        {
            "A": [0.10, -0.10, 0.00],
            "B": [0.00, 0.02, -0.04],
        }
    )

    portfolio = calculate_portfolio_returns(
        returns,
        {"A": 0.6, "B": 0.4},
    )

    assert portfolio.tolist() == pytest.approx([0.06, -0.052, -0.016])


def test_calculate_portfolio_returns_rejects_missing_values():
    returns = pd.DataFrame({"A": [0.01, np.nan]})

    with pytest.raises(ValueError, match="missing asset returns"):
        calculate_portfolio_returns(returns, {"A": 1.0})
