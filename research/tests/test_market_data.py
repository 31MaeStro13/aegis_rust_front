import pandas as pd
import pytest

from research.src import market_data
from research.src.market_data import fetch_history, save_history_cache


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
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
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
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
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
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    with pytest.raises(ValueError, match="duplicate"):
        fetch_history("SBER", "shares", "2026-09-01", "2026-09-10")


def test_fetch_history_retrieves_multiple_pages(monkeypatch):
    class FakeResponse:
        def __init__(self, start):
            self.start = start

        def raise_for_status(self):
            pass

        def json(self):
            if self.start == 0:
                rows = [
                    ["2026-09-01", "SBER", "TQBR", 300.0],
                    ["2026-09-02", "SBER", "TQBR", 301.0],
                ]
            else:
                rows = [
                    ["2026-09-03", "SBER", "TQBR", 302.0],
                ]

            total = 3

            return {
                "history": {
                    "columns": [
                        "TRADEDATE", "SECID", "BOARDID", "CLOSE"
                    ],
                    "data": rows,
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[self.start, total, 2]],
                },
            }

    class FakeSession:
        def __init__(self):
            self.starts = []

        def mount(self, prefix, adapter):
            pass

        def get(self, url, params, timeout):
            start = params["start"]
            self.starts.append(start)
            return FakeResponse(start)

        def close(self):
            pass

    session = FakeSession()

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: session,
    )

    result = fetch_history(
        "SBER",
        "shares",
        "2026-09-01",
        "2026-09-10",
    )

    assert len(result) == 3
    assert result["CLOSE"].tolist() == [300.0, 301.0, 302.0]
    assert session.starts == [0, 2]


def test_fetch_history_rejects_premature_empty_page(monkeypatch):
    class FakeResponse:
        def __init__(self, start):
            self.start = start

        def raise_for_status(self):
            pass

        def json(self):
            if self.start == 0:
                rows = [
                    ["2026-09-01", "SBER", "TQBR", 300.0],
                    ["2026-09-02", "SBER", "TQBR", 301.0],
                ]
            else:
                rows = []

            return {
                "history": {
                    "columns": [
                        "TRADEDATE", "SECID", "BOARDID", "CLOSE"
                    ],
                    "data": rows,
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[self.start, 3, 2]],
                },
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            pass

        def get(self, url, params, timeout):
            return FakeResponse(params["start"])

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    with pytest.raises(
        ValueError,
        match="empty page before",
    ):
        fetch_history(
            "SBER",
            "shares",
            "2026-09-01",
            "2026-09-10",
        )


def test_fetch_history_supports_bonds_market(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "history": {
                    "columns": [
                        "TRADEDATE",
                        "SECID",
                        "BOARDID",
                        "CLOSE",
                    ],
                    "data": [
                        ["2026-09-01", "SU26238RMFS4", "TQOB", 950.25],
                    ],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 1, 100]],
                },
            }

    class FakeSession:
        def __init__(self):
            self.url = None
            self.params = None

        def mount(self, prefix, adapter):
            pass

        def get(self, url, params, timeout):
            self.url = url
            self.params = params
            return FakeResponse()

        def close(self):
            pass

    session = FakeSession()

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: session,
    )

    result = fetch_history(
        "SU26238RMFS4",
        "bonds",
        "2026-09-01",
        "2026-09-10",
        board="TQOB",
    )

    assert len(result) == 1
    assert result["CLOSE"].tolist() == [950.25]
    assert "/markets/bonds/" in session.url
    assert "/boards/TQOB/" in session.url
    assert "/securities/SU26238RMFS4.json" in session.url


def test_fetch_history_configures_http_retries(monkeypatch):
    mounted_adapters = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "history": {
                    "columns": [
                        "TRADEDATE",
                        "SECID",
                        "CLOSE",
                    ],
                    "data": [
                        ["2026-09-01", "SBER", 300.0],
                    ],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 1, 100]],
                },
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            mounted_adapters[prefix] = adapter

        def get(self, url, params, timeout):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    fetch_history(
        "SBER",
        "shares",
        "2026-09-01",
        "2026-09-10",
    )

    assert set(mounted_adapters) == {"https://", "http://"}

    for adapter in mounted_adapters.values():
        retry = adapter.max_retries

        assert retry.total == 5
        assert retry.backoff_factor == 0.5
        assert set(retry.status_forcelist) == {
            429, 500, 502, 503, 504
        }
        assert "GET" in retry.allowed_methods
        assert retry.respect_retry_after_header is True


def test_fetch_history_rejects_infinite_close(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "history": {
                    "columns": ["TRADEDATE", "SECID", "CLOSE"],
                    "data": [
                        ["2026-09-01", "SBER", float("inf")],
                    ],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 1, 100]],
                },
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    with pytest.raises(ValueError, match="non-finite"):
        fetch_history(
            "SBER",
            "shares",
            "2026-09-01",
            "2026-09-10",
        )


def test_save_history_cache_rejects_infinite_close(tmp_path):
    df = pd.DataFrame(
        {
            "TRADEDATE": ["2026-09-01"],
            "SECID": ["SBER"],
            "CLOSE": [float("inf")],
        }
    )

    with pytest.raises(ValueError, match="non-finite"):
        save_history_cache(
            df,
            "SBER",
            cache_dir=tmp_path,
        )

    assert not list(tmp_path.glob("*.csv"))


def test_fetch_bond_history_preserves_additional_fields(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "history": {
                    "columns": [
                        "TRADEDATE",
                        "SECID",
                        "BOARDID",
                        "CLOSE",
                        "LEGALCLOSEPRICE",
                        "ACCINT",
                    ],
                    "data": [
                        [
                            "2026-03-19",
                            "SU26238RMFS4",
                            "TQOB",
                            60.287,
                            60.043,
                            20.62,
                        ],
                    ],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 1, 100]],
                },
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    result = fetch_history(
        "SU26238RMFS4",
        "bonds",
        "2026-03-19",
        "2026-03-19",
        board="TQOB",
    )

    assert result.loc[0, "LEGALCLOSEPRICE"] == 60.043
    assert result.loc[0, "ACCINT"] == 20.62


def test_fetch_bond_history_preserves_missing_close_at_maturity(
    monkeypatch,
):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "history": {
                    "columns": [
                        "TRADEDATE",
                        "SECID",
                        "BOARDID",
                        "CLOSE",
                        "LEGALCLOSEPRICE",
                        "ACCINT",
                    ],
                    "data": [
                        [
                            "2026-03-25",
                            "SU29014RMFS6",
                            "TQOB",
                            None,
                            99.998,
                            0.0,
                        ],
                    ],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 1, 100]],
                },
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    result = fetch_history(
        "SU29014RMFS6",
        "bonds",
        "2026-03-25",
        "2026-03-25",
        board="TQOB",
    )

    assert pd.isna(result.loc[0, "CLOSE"])
    assert result.loc[0, "LEGALCLOSEPRICE"] == 99.998
    assert result.loc[0, "ACCINT"] == 0.0


def test_fetch_share_history_still_rejects_missing_close(
    monkeypatch,
):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "history": {
                    "columns": ["TRADEDATE", "SECID", "CLOSE"],
                    "data": [["2026-09-01", "SBER", None]],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 1, 100]],
                },
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    with pytest.raises(ValueError, match="missing or non-finite"):
        fetch_history(
            "SBER",
            "shares",
            "2026-09-01",
            "2026-09-01",
        )


def test_save_bond_cache_accepts_missing_close_at_maturity(tmp_path):
    df = pd.DataFrame(
        {
            "TRADEDATE": ["2026-03-25"],
            "SECID": ["SU29014RMFS6"],
            "BOARDID": ["TQOB"],
            "CLOSE": [float("nan")],
            "LEGALCLOSEPRICE": [99.998],
            "ACCINT": [0.0],
        }
    )

    output_path = save_history_cache(
        df,
        "SU29014RMFS6",
        cache_dir=tmp_path,
        board="TQOB",
        market="bonds",
    )

    saved = pd.read_csv(output_path)

    assert len(saved) == 1
    assert pd.isna(saved.loc[0, "CLOSE"])
    assert saved.loc[0, "LEGALCLOSEPRICE"] == pytest.approx(99.998)
    assert saved.loc[0, "ACCINT"] == pytest.approx(0.0)
    assert saved.loc[0, "SECID"] == "SU29014RMFS6"


def test_save_share_cache_rejects_missing_close(tmp_path):
    df = pd.DataFrame(
        {
            "TRADEDATE": ["2026-03-25"],
            "SECID": ["SBER"],
            "CLOSE": [float("nan")],
        }
    )

    with pytest.raises(ValueError, match="non-finite"):
        save_history_cache(
            df,
            "SBER",
            cache_dir=tmp_path,
            market="shares",
        )

    assert not list(tmp_path.glob("*.csv"))


@pytest.mark.parametrize(
    "invalid_accint",
    ["invalid", float("nan"), float("inf"), -1.0],
)
def test_save_bond_cache_rejects_invalid_accint(
    tmp_path,
    invalid_accint,
):
    df = pd.DataFrame(
        {
            "TRADEDATE": ["2026-03-25"],
            "SECID": ["SU29014RMFS6"],
            "BOARDID": ["TQOB"],
            "CLOSE": [float("nan")],
            "LEGALCLOSEPRICE": [99.998],
            "ACCINT": [invalid_accint],
        }
    )

    with pytest.raises(
        ValueError,
        match="ACCINT",
    ):
        save_history_cache(
            df,
            "SU29014RMFS6",
            cache_dir=tmp_path,
            board="TQOB",
            market="bonds",
        )

    assert not list(tmp_path.glob("*.csv"))


def test_fetch_history_returns_bond_columns_when_history_is_empty(
    monkeypatch,
):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "history": {
                    "columns": [
                        "TRADEDATE",
                        "SECID",
                        "CLOSE",
                        "LEGALCLOSEPRICE",
                        "ACCINT",
                    ],
                    "data": [],
                },
                "history.cursor": {
                    "columns": ["START", "TOTAL", "PAGESIZE"],
                    "data": [[0, 0, 100]],
                },
            }

    class FakeSession:
        def mount(self, prefix, adapter):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        market_data.requests,
        "Session",
        lambda: FakeSession(),
    )

    result = fetch_history(
        "SU29014RMFS6",
        "bonds",
        "2026-03-01",
        "2026-03-31",
    )

    assert result.empty
    assert list(result.columns) == [
        "TRADEDATE",
        "SECID",
        "CLOSE",
        "LEGALCLOSEPRICE",
        "ACCINT",
    ]


def test_save_history_cache_rejects_mismatched_security_id(tmp_path):
    df = pd.DataFrame(
        {
            "TRADEDATE": ["2026-03-25"],
            "SECID": ["GAZP"],
            "CLOSE": [150.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="SECID values must match",
    ):
        save_history_cache(
            df,
            "SBER",
            cache_dir=tmp_path,
            market="shares",
        )

    assert not list(tmp_path.glob("*.csv"))
