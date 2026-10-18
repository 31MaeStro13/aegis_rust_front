import pandas as pd
import pytest

from research.src.market_data import fetch_history


def test_fetch_history_returns_clean_data(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
    "history": {
        "columns": ["TRADEDATE", "SECID", "CLOSE"],
        "data": [
            ["2026-01-05", "SBER", 300.0],
            ["2026-01-06", "SBER", 305.0],
        ],
    },
    "history.cursor": {
        "columns": ["START", "TOTAL", "PAGESIZE"],
        "data": [[0, 2, 100]],
    },
}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        "research.src.market_data.requests.Session",
        lambda: FakeSession(),
    )

    result = fetch_history(
        "SBER", "shares", "2026-09-01", "2026-09-10"
    )

    assert len(result) == 2
    assert result["TRADEDATE"].is_monotonic_increasing
    assert result["CLOSE"].tolist() == [300.0, 305.0]
    assert pd.api.types.is_datetime64_any_dtype(result["TRADEDATE"])


def test_fetch_history_rejects_invalid_market():
    with pytest.raises(ValueError, match="market"):
        fetch_history("SBER", "invalid", "2026-09-01", "2026-09-10")

def test_fetch_history_rejects_reversed_dates():
    with pytest.raises(ValueError, match="start_date"):
        fetch_history("SBER", "shares", "2026-09-10", "2026-09-01")


def test_fetch_history_rejects_nonpositive_close(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
    "history": {
        "columns": ["TRADEDATE", "SECID", "CLOSE"],
        "data": [
            ["2026-09-01", "SBER", 0.0],
        ],
    },
    "history.cursor": {
        "columns": ["START", "TOTAL", "PAGESIZE"],
        "data": [[0, 1, 100]],
    },
}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        "research.src.market_data.requests.Session",
        lambda: FakeSession(),
    )

    with pytest.raises(ValueError, match="positive"):
        fetch_history("SBER", "shares", "2026-09-01", "2026-09-10")


def test_fetch_history_rejects_duplicate_dates(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        
        def json(self):
            return {
                "history": {
                    "columns": ["TRADEDATE", "SECID", "CLOSE"],
                    "data": [
                        ["2026-09-01", "SBER", 272.21],
                        ["2026-09-01", "SBER", 272.21],
                    ],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 2, 100]],
                },
            }


    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        "research.src.market_data.requests.Session",
        lambda: FakeSession(),
    )

    with pytest.raises(ValueError, match="duplicate"):
        fetch_history("SBER", "shares", "2026-09-01", "2026-09-10")
