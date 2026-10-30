
import numpy as np
import pandas as pd
import pytest

from research.src.portfolio_returns import (
    align_asset_returns,
    build_asset_returns,
    calculate_bond_total_returns,
    calculate_buy_and_hold_returns,
    calculate_portfolio_returns,
    load_close_series,
    validate_weights,
)


def test_load_close_series_preserves_missing_close(tmp_path):
    history = pd.DataFrame(
        {
            "TRADEDATE": ["2026-03-24", "2026-03-25"],
            "CLOSE": [99.997, np.nan],
            "LEGALCLOSEPRICE": [99.998, 99.998],
            "ACCINT": [38.29, 0.0],
        }
    )
    path = tmp_path / "bond_history.csv"
    history.to_csv(path, index=False)

    prices = load_close_series(
        str(path),
        security="SU29014RMFS6",
        price_multiplier=10.0,
    )

    assert prices.iloc[0] == pytest.approx(999.97)
    assert np.isnan(prices.iloc[1])


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

def test_bond_total_returns_include_coupon_cash_flows():
    from research.src.portfolio_returns import calculate_bond_total_returns

    dirty_prices = pd.Series([1000.0, 990.0], index=pd.date_range("2026-01-01", periods=2))
    cash_flows = pd.Series([0.0, 10.0], index=dirty_prices.index)

    returns = calculate_bond_total_returns(dirty_prices, cash_flows)

    assert np.isnan(returns.iloc[0])
    assert returns.iloc[1] == pytest.approx(0.0)


def test_bond_total_returns_preserve_missing_market_prices():
    dates = pd.date_range("2026-03-23", periods=3)
    dirty_prices = pd.Series([1000.0, np.nan, 1010.0], index=dates)
    cash_flows = pd.Series([0.0, 0.0, 0.0], index=dates)

    returns = calculate_bond_total_returns(dirty_prices, cash_flows)

    assert np.isnan(returns.iloc[0])
    assert np.isnan(returns.iloc[1])
    assert np.isnan(returns.iloc[2])


def test_bond_maturity_cash_flow_preserves_missing_market_prices():
    dates = pd.to_datetime(
        ["2026-03-23", "2026-03-24", "2026-03-25"]
    )

    dirty_prices = pd.Series(
        [999.98 + 37.89, np.nan, np.nan],
        index=dates,
    )
    coupons = pd.Series([0.0, 0.0, 38.70], index=dates)
    redemptions = pd.Series([0.0, 0.0, 1000.0], index=dates)

    returns = calculate_bond_total_returns(
        dirty_prices,
        coupons,
        redemption_cash_flows=redemptions,
    )

    assert np.isnan(returns.iloc[0])
    assert np.isnan(returns.iloc[1])
    assert np.isnan(returns.iloc[2])
    assert dirty_prices.isna().iloc[1:].all()
    assert coupons.iloc[2] + redemptions.iloc[2] == pytest.approx(1038.70)


def test_bond_redemption_calculates_terminal_return_without_market_price():
    dates = pd.date_range("2026-03-24", periods=2)

    dirty_prices = pd.Series([1000.0, np.nan], index=dates)
    coupons = pd.Series([0.0, 38.70], index=dates)
    redemptions = pd.Series([0.0, 1000.0], index=dates)

    returns = calculate_bond_total_returns(
        dirty_prices,
        coupons,
        redemption_cash_flows=redemptions,
    )

    assert np.isnan(returns.iloc[0])
    assert returns.iloc[1] == pytest.approx(0.0387)


def test_bond_redemption_preserves_missing_previous_market_price():
    dates = pd.date_range("2026-03-23", periods=3)

    dirty_prices = pd.Series(
        [1000.0, np.nan, np.nan],
        index=dates,
    )
    coupons = pd.Series([0.0, 0.0, 38.70], index=dates)
    redemptions = pd.Series([0.0, 0.0, 1000.0], index=dates)

    returns = calculate_bond_total_returns(
        dirty_prices,
        coupons,
        redemption_cash_flows=redemptions,
    )

    assert np.isnan(returns.iloc[0])
    assert np.isnan(returns.iloc[1])
    assert np.isnan(returns.iloc[2])


def test_buy_and_hold_returns_allow_weights_to_drift():
    from research.src.portfolio_returns import calculate_buy_and_hold_returns

    asset_returns = pd.DataFrame(
        {
            "A": [0.20, 0.00],
            "B": [0.00, 0.10],
        },
        index=pd.date_range("2026-01-01", periods=2),
    )

    returns = calculate_buy_and_hold_returns(
        asset_returns,
        {"A": 0.5, "B": 0.5},
    )

    assert returns.iloc[0] == pytest.approx(0.10)
    assert returns.iloc[1] == pytest.approx(0.05 / 1.10)
