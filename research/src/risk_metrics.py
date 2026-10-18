"""Deterministic portfolio risk metrics for Aegis Wealth Terminal."""

import numpy as np


def calculate_hhi(weights):
    """Calculate the Herfindahl-Hirschman Index from percentage weights.

    Parameters
    ----------
    weights : array-like
        Portfolio weights expressed in percentage points, such as 45.825.

    Returns
    -------
    float
        Sum of squared percentage weights.

    Raises
    ------
    ValueError
        If weights are empty, non-finite, negative, or do not sum to 100%.
    """
    weights = np.asarray(weights, dtype=float)

    if weights.ndim != 1 or weights.size == 0:
        raise ValueError("Weights must be a non-empty one-dimensional array.")

    if not np.isfinite(weights).all():
        raise ValueError("Weights must contain only finite values.")

    if (weights < 0).any():
        raise ValueError("Weights cannot be negative.")

    if not np.isclose(weights.sum(), 100.0, atol=0.001):
        raise ValueError("Portfolio weights must sum to 100%.")

    return float(np.sum(weights**2))


def classify_hhi(hhi):
    """Classify HHI using the thresholds specified for this project."""
    if not np.isfinite(hhi) or hhi < 0:
        raise ValueError("HHI must be a finite, non-negative number.")

    if hhi < 1500:
        return "Low"
    if hhi < 2500:
        return "Medium"
    return "High"


def daily_returns(prices):
    """Calculate simple daily returns from a sequence of closing prices."""
    prices = np.asarray(prices, dtype=float)

    if prices.ndim != 1 or prices.size < 2:
        raise ValueError("At least two closing prices are required.")

    if not np.isfinite(prices).all():
        raise ValueError("Prices must contain only finite values.")

    if (prices <= 0).any():
        raise ValueError("Closing prices must be positive.")

    return prices[1:] / prices[:-1] - 1.0


def annualized_volatility(returns):
    """Calculate annualized volatility from daily returns."""
    returns = np.asarray(returns, dtype=float)

    if returns.ndim != 1 or returns.size < 2:
        raise ValueError("At least two daily returns are required.")

    if not np.isfinite(returns).all():
        raise ValueError("Returns must contain only finite values.")

    return float(np.std(returns, ddof=1) * np.sqrt(252))


def calculate_beta(asset_returns, benchmark_returns):
    """Calculate asset beta relative to matched benchmark returns."""
    asset_returns = np.asarray(asset_returns, dtype=float)
    benchmark_returns = np.asarray(benchmark_returns, dtype=float)

    if (
        asset_returns.ndim != 1
        or benchmark_returns.ndim != 1
        or asset_returns.size != benchmark_returns.size
        or asset_returns.size < 2
    ):
        raise ValueError(
            "Asset and benchmark returns must be equal-length "
            "one-dimensional arrays with at least two observations."
        )

    if not (
        np.isfinite(asset_returns).all()
        and np.isfinite(benchmark_returns).all()
    ):
        raise ValueError("Returns must contain only finite values.")

    benchmark_variance = np.var(benchmark_returns, ddof=1)

    if benchmark_variance <= 0:
        raise ValueError("Benchmark returns must have positive variance.")

    return float(
        np.cov(asset_returns, benchmark_returns, ddof=1)[0, 1]
        / benchmark_variance
    )

