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


def portfolio_daily_returns(asset_returns, weights):
    """Calculate daily portfolio returns using fixed portfolio weights.

    Parameters
    ----------
    asset_returns : array-like, shape (days, assets)
        Daily returns for each asset, with one column per asset.
    weights : array-like, shape (assets,)
        Portfolio weights as fractions, such as 0.45 for 45%.

    Notes
    -----
    This function assumes constant weights each day (daily rebalancing
    to the specified weights). It does not model buy-and-hold drift.
    """
    returns = np.asarray(asset_returns, dtype=float)
    weights = np.asarray(weights, dtype=float)

    if returns.ndim != 2 or returns.shape[0] < 1 or returns.shape[1] < 1:
        raise ValueError("asset_returns must be a non-empty 2D array.")

    if weights.ndim != 1 or weights.size != returns.shape[1]:
        raise ValueError("One weight is required for each asset.")

    if not np.isfinite(returns).all():
        raise ValueError("Asset returns must be finite.")

    if not np.isfinite(weights).all():
        raise ValueError("Weights must be finite.")

    if (weights < 0).any():
        raise ValueError("Weights cannot be negative.")

    if not np.isclose(weights.sum(), 1.0, atol=1e-6):
        raise ValueError("Weights must sum to 1.0.")

    return returns @ weights


def historical_var(returns, confidence_level=0.95):
    """Historical Value at Risk as a positive loss fraction."""
    returns = np.asarray(returns, dtype=float)

    if returns.ndim != 1 or returns.size < 2:
        raise ValueError("At least two portfolio returns are required.")

    if not np.isfinite(returns).all():
        raise ValueError("Returns must contain only finite values.")

    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1.")

    return float(max(0.0, -np.quantile(returns, 1 - confidence_level)))


def historical_cvar(returns, confidence_level=0.95):
    """Historical CVaR/Expected Shortfall as a positive loss fraction.

    Uses the average loss among returns at or below the empirical
    return quantile for the requested tail probability.
    """
    returns = np.asarray(returns, dtype=float)

    if returns.ndim != 1 or returns.size < 2:
        raise ValueError("At least two portfolio returns are required.")

    if not np.isfinite(returns).all():
        raise ValueError("Returns must contain only finite values.")

    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1.")

    cutoff = np.quantile(returns, 1 - confidence_level)
    tail_returns = returns[returns <= cutoff]

    if tail_returns.size == 0:
        raise ValueError("No observations in the selected loss tail.")

    return float(max(0.0, -tail_returns.mean()))


def parametric_var(returns, confidence_level=0.95):
    """Normal-distribution VaR as a positive loss fraction."""
    from statistics import NormalDist

    returns = np.asarray(returns, dtype=float)

    if returns.ndim != 1 or returns.size < 2:
        raise ValueError("At least two portfolio returns are required.")

    if not np.isfinite(returns).all():
        raise ValueError("Returns must contain only finite values.")

    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1.")

    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))
    z_score = NormalDist().inv_cdf(confidence_level)

    return float(max(0.0, -(mean - z_score * std)))


def parametric_cvar(returns, confidence_level=0.95):
    """Normal-distribution CVaR/Expected Shortfall as a positive loss fraction."""
    from math import exp, pi, sqrt
    from statistics import NormalDist

    returns = np.asarray(returns, dtype=float)

    if returns.ndim != 1 or returns.size < 2:
        raise ValueError("At least two portfolio returns are required.")

    if not np.isfinite(returns).all():
        raise ValueError("Returns must contain only finite values.")

    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1.")

    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))

    if std == 0:
        return float(max(0.0, -mean))

    z_score = NormalDist().inv_cdf(confidence_level)
    density = exp(-0.5 * z_score**2) / sqrt(2 * pi)

    return float(max(0.0, -mean + std * density / (1 - confidence_level)))
