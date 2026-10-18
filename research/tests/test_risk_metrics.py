import numpy as np
import pytest

from research.src.risk_metrics import (
    calculate_hhi,
    classify_hhi,
    daily_returns,
    annualized_volatility,
    calculate_beta,
)

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
