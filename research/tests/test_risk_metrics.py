import numpy as np
import pytest

from research.src.risk_metrics import (
    calculate_beta,
    calculate_hhi,
    classify_hhi,
    daily_returns,
    annualized_volatility,
    portfolio_daily_returns,
    historical_var,
    historical_cvar,
    parametric_var,
    parametric_cvar,
)

def test_portfolio_daily_returns_with_fixed_weights():
    asset_returns = np.array([
        [0.10, 0.00],
        [-0.10, 0.02],
        [0.00, -0.04],
    ])
    weights = [0.60, 0.40]

    result = portfolio_daily_returns(asset_returns, weights)

    np.testing.assert_allclose(result, [0.06, -0.052, -0.016])


def test_portfolio_daily_returns_rejects_weights_not_summing_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        portfolio_daily_returns([[0.01, 0.02]], [0.6, 0.3])


def test_historical_var_and_cvar_known_losses():
    returns = np.array([-0.10, -0.05, -0.02, 0.01, 0.03])

    assert np.isclose(historical_var(returns, 0.80), 0.06)
    assert np.isclose(historical_cvar(returns, 0.80), 0.10)



def test_parametric_var_known_result():
    returns = np.array([-0.03, -0.01, 0.00, 0.01, 0.02])

    result = parametric_var(returns, 0.95)

    # Normal-distribution VaR, expressed as a positive loss fraction.
    assert np.isclose(result, 0.03363, atol=0.00002)


def test_parametric_cvar_known_result():
    returns = np.array([-0.03, -0.01, 0.00, 0.01, 0.02])

    result = parametric_cvar(returns, 0.95)

    # Normal-distribution Expected Shortfall, expressed as a positive loss.
    assert np.isclose(result, 0.04169, atol=0.00002)



@pytest.mark.parametrize("function", [
    historical_var,
    historical_cvar,
    parametric_var,
    parametric_cvar,
])
def test_var_and_cvar_reject_invalid_confidence(function):
    with pytest.raises(ValueError, match="confidence_level"):
        function([-0.01, 0.01], 1.0)


def test_dataset_a_hhi():
    weights = [45.825, 26.040, 20.550, 7.585]
    assert np.isclose(calculate_hhi(weights), 3257.85, atol=0.01)


def test_dataset_b_hhi():
    weights = [27.010, 24.625, 18.240, 15.275, 14.850]
    assert np.isclose(calculate_hhi(weights), 2122.48, atol=0.01)


@pytest.mark.parametrize(
    ("hhi", "expected"),
    [
        (1499.0, "Low"),
        (1500.0, "Medium"),
        (2499.99, "Medium"),
        (2500.0, "High"),
    ],
)
def test_hhi_classification(hhi, expected):
    assert classify_hhi(hhi) == expected


def test_hhi_rejects_weights_not_summing_to_100():
    with pytest.raises(ValueError):
        calculate_hhi([50, 30])


def test_hhi_rejects_negative_weights():
    with pytest.raises(ValueError):
        calculate_hhi([110, -10])


def test_hhi_rejects_non_finite_weights():
    with pytest.raises(ValueError):
        calculate_hhi([50, np.nan, 50])


def test_daily_returns():
    prices = [100, 110, 99]
    result = daily_returns(prices)

    np.testing.assert_allclose(result, [0.10, -0.10])


def test_daily_returns_rejects_nonpositive_prices():
    with pytest.raises(ValueError, match="positive"):
        daily_returns([100, 0, 105])


def test_annualized_volatility():
    returns = [0.01, -0.01, 0.02, -0.02]
    result = annualized_volatility(returns)

    expected = np.std(returns, ddof=1) * np.sqrt(252)
    assert np.isclose(result, expected)


def test_beta_with_known_relationship():
    benchmark = np.array([-0.02, -0.01, 0.01, 0.02])
    asset = 2.0 * benchmark

    result = calculate_beta(asset, benchmark)

    assert np.isclose(result, 2.0)


def test_beta_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="equal-length"):
        calculate_beta([0.01, 0.02], [0.01, 0.02, 0.03])


def test_beta_rejects_constant_benchmark():
    with pytest.raises(ValueError, match="positive variance"):
        calculate_beta([0.01, 0.02, 0.03], [0.01, 0.01, 0.01])


def test_historical_var_known_values():
    returns = np.array([-0.10, -0.05, 0.00, 0.02, 0.04])
    result = historical_var(returns, confidence_level=0.80)
    assert result == pytest.approx(0.06)


def test_historical_cvar_known_values():
    returns = np.array([-0.10, -0.05, 0.00, 0.02, 0.04])
    result = historical_cvar(returns, confidence_level=0.80)
    assert result == pytest.approx(0.10)


def test_var_rejects_invalid_confidence_level():
    returns = np.array([-0.02, 0.01, 0.03])

    with pytest.raises(ValueError):
        historical_var(returns, confidence_level=1.0)

    with pytest.raises(ValueError):
        parametric_var(returns, confidence_level=0.0)


def test_cvar_rejects_non_finite_returns():
    returns = np.array([-0.02, np.nan, 0.03])

    with pytest.raises(ValueError):
        historical_cvar(returns)

    with pytest.raises(ValueError):
        parametric_cvar(returns)


def test_portfolio_daily_returns_rejects_weights_not_summing_to_one():
    asset_returns = np.array([
        [0.01, 0.02],
        [-0.01, 0.03],
    ])

    with pytest.raises(ValueError, match="sum to 1.0"):
        portfolio_daily_returns(asset_returns, [0.40, 0.40])