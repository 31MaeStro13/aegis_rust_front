
"""MOEX ISS historical market-data retrieval, validation, and caching."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


BASE_URL = "https://iss.moex.com/iss"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"
PAGE_SIZE = 100


def fetch_history(
    security: str,
    market: str,
    start_date: str,
    end_date: str,
    *,
    board: str | None = None,
    timeout: int = 30,
    max_pages: int = 100,
):
    """Fetch and validate historical prices from the MOEX ISS API."""

    try:
        start_timestamp = pd.Timestamp(start_date)
        end_timestamp = pd.Timestamp(end_date)
    except (TypeError, ValueError):
        raise ValueError(
            "start_date and end_date must be valid dates"
        ) from None

    if pd.isna(start_timestamp) or pd.isna(end_timestamp):
        raise ValueError(
            "start_date and end_date must be valid dates"
        )

    if start_timestamp > end_timestamp:
        raise ValueError("start_date must not be after end_date")

    if market not in {"shares", "index", "bonds"}:
        raise ValueError(
            "Invalid market; use 'shares', 'index', or 'bonds'"
        )

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    endpoint = (
        f"{BASE_URL}/history/engines/stock/markets/"
        f"{market}/"
    )
    if board:
        endpoint += f"boards/{board}/"
    endpoint += f"securities/{security}.json"

    params_base = {
        "from": start_date,
        "till": end_date,
        "start": 0,
        "iss.meta": "off",
        "iss.only": "history,history.cursor",
        "history.columns": (
        "TRADEDATE,SECID,BOARDID,CLOSE,LEGALCLOSEPRICE,ACCINT"
        if market == "bonds"
        else "TRADEDATE,SECID,BOARDID,CLOSE"
        ),
    }

    all_rows = []
    expected_columns = None
    expected_total = None
    start = 0
    pages_retrieved = 0


    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        while True:
            if pages_retrieved >= max_pages:
                raise RuntimeError(
                    f"Reached max_pages={max_pages}; "
                    "historical data may be incomplete"
                )

            params = {**params_base, "start": start}
            response = session.get(
                endpoint,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()

            history = payload.get("history")
            if not isinstance(history, dict):
                raise ValueError(
                    "MOEX response has no valid history section"
                )

            returned_columns = history.get("columns", [])
            page = history.get("data", [])

            cursor_section = payload.get("history.cursor", {})
            cursor_rows = cursor_section.get("data", [])
            if not cursor_rows:
                raise ValueError(
                    "MOEX response has no valid history.cursor data"
                )

            cursor_columns = cursor_section.get("columns", [])
            cursor = dict(zip(cursor_columns, cursor_rows[0]))
            total = int(cursor.get("TOTAL", 0))
            page_start = int(cursor.get("START", start))

            if expected_total is None:
                expected_total = total
            elif total != expected_total:
                raise ValueError(
                    "MOEX history total changed during pagination"
                )

            if not page:
                if total == 0 and not all_rows:
                    break

                if page_start < total:
                    raise ValueError(
                        "MOEX returned an empty page before "
                        "all expected history records were retrieved"
                    )

                break

            if expected_columns is None:
                expected_columns = returned_columns
            elif returned_columns != expected_columns:
                raise ValueError(
                    "MOEX history columns changed between pages"
                )

            all_rows.extend(page)
            pages_retrieved += 1

            if page_start + len(page) >= total:
                break

            next_start = page_start + len(page)
            if next_start <= start:
                raise ValueError(
                    "MOEX pagination did not advance"
                )
            start = next_start
    finally:
        session.close()

    if not all_rows:
        empty_columns = ["TRADEDATE", "SECID", "CLOSE"]

        if market == "bonds":
            empty_columns.extend(
                ["LEGALCLOSEPRICE", "ACCINT"]
            )

        return pd.DataFrame(columns=empty_columns)

    df = pd.DataFrame(all_rows, columns=expected_columns)

    required = {"TRADEDATE", "SECID", "CLOSE"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            f"MOEX history is missing required columns: {sorted(missing)}"
        )

    df["TRADEDATE"] = pd.to_datetime(
        df["TRADEDATE"], errors="coerce"
    )
    df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")

    if df["TRADEDATE"].isna().any():
        raise ValueError("MOEX history contains invalid trade dates")

    if market == "bonds":
        if "LEGALCLOSEPRICE" in df.columns:
            df["LEGALCLOSEPRICE"] = pd.to_numeric(
                df["LEGALCLOSEPRICE"], errors="coerce"
            )

        if "ACCINT" in df.columns:
            df["ACCINT"] = pd.to_numeric(
                df["ACCINT"], errors="coerce"
            )

        valid_close = np.isfinite(df["CLOSE"]) & (df["CLOSE"] > 0)

        if "LEGALCLOSEPRICE" in df.columns:
            valid_legal_close = (
                np.isfinite(df["LEGALCLOSEPRICE"])
                & (df["LEGALCLOSEPRICE"] > 0)
            )
        else:
            valid_legal_close = pd.Series(False, index=df.index)

        if not (valid_close | valid_legal_close).all():
            raise ValueError(
                "MOEX bond history contains rows without a valid "
                "CLOSE or LEGALCLOSEPRICE"
            )
    else:
        if not np.isfinite(df["CLOSE"]).all():
            raise ValueError(
                "MOEX history contains missing or non-finite close prices"
            )

        if (df["CLOSE"] <= 0).any():
            raise ValueError("MOEX history contains nonpositive close prices")

    if df["TRADEDATE"].duplicated().any():
        raise ValueError("MOEX history contains duplicate trade dates")

    df = df.sort_values("TRADEDATE").reset_index(drop=True)
    return df


def save_history_cache(
    df: pd.DataFrame,
    security: str,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    *,
    board: str | None = None,
    market: str = "shares",
) -> Path:
    """Validate and save historical market data as a CSV file."""
    if not security or not security.strip():
        raise ValueError("security must not be empty")

    if df.empty:
        raise ValueError("Cannot cache an empty DataFrame")

    required = {"TRADEDATE", "SECID", "CLOSE"}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )
    requested_security = security.strip().upper()
    raw_securities = df["SECID"]

    if raw_securities.isna().any():
        raise ValueError(
            "SECID values must match the requested security"
        )

    returned_securities = (
        raw_securities.astype(str).str.strip().str.upper()
    )

    if (
        returned_securities.eq("").any()
        or returned_securities.ne(requested_security).any()
    ):
        raise ValueError(
            "SECID values must match the requested security"
        )
    returned_securities = (
        df["SECID"].astype(str).str.strip().str.upper()
    )

    if (
        returned_securities.isna().any()
        or returned_securities.ne(requested_security).any()
    ):
        raise ValueError(
            "SECID values must match the requested security"
        )

    clean_df = df.copy()
    clean_df["TRADEDATE"] = pd.to_datetime(
        clean_df["TRADEDATE"], errors="coerce"
    )

    if clean_df["TRADEDATE"].isna().any():
        raise ValueError("TRADEDATE contains invalid dates")

    if clean_df["TRADEDATE"].duplicated().any():
        raise ValueError("TRADEDATE contains duplicate dates")

    if market not in {"shares", "index", "bonds"}:
        raise ValueError(
            "market must be one of: shares, index, bonds"
        )

    clean_df["CLOSE"] = pd.to_numeric(
        clean_df["CLOSE"], errors="coerce"
    )

    if market == "bonds" and "ACCINT" in clean_df.columns:
        clean_df["ACCINT"] = pd.to_numeric(
            clean_df["ACCINT"], errors="coerce"
        )

        if (
            not np.isfinite(clean_df["ACCINT"]).all()
            or (clean_df["ACCINT"] < 0).any()
        ):
            raise ValueError(
                "ACCINT must contain finite, non-negative values"
            )

    valid_close = (
        np.isfinite(clean_df["CLOSE"])
        & (clean_df["CLOSE"] > 0)
    )

    if market == "bonds":
        if "LEGALCLOSEPRICE" in clean_df.columns:
            clean_df["LEGALCLOSEPRICE"] = pd.to_numeric(
                clean_df["LEGALCLOSEPRICE"], errors="coerce"
            )

            valid_legal_close = (
                np.isfinite(clean_df["LEGALCLOSEPRICE"])
                & (clean_df["LEGALCLOSEPRICE"] > 0)
            )
        else:
            valid_legal_close = pd.Series(
                False, index=clean_df.index
            )

        if not (valid_close | valid_legal_close).all():
            raise ValueError(
                "Bond rows must have a valid CLOSE "
                "or LEGALCLOSEPRICE"
            )
    else:
        if not np.isfinite(clean_df["CLOSE"]).all():
            raise ValueError(
                "CLOSE contains missing or non-finite prices"
            )

        if (clean_df["CLOSE"] <= 0).any():
            raise ValueError("CLOSE must contain positive prices")

    clean_df = clean_df.sort_values("TRADEDATE").reset_index(drop=True)
    clean_df["TRADEDATE"] = clean_df["TRADEDATE"].dt.strftime("%Y-%m-%d")

    output_dir = Path(cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = f"_{board.strip().upper()}" if board else ""
    filename = f"{security.strip().upper()}{suffix}_history.csv"
    output_file = output_dir / filename

    clean_df.to_csv(output_file, index=False, encoding="utf-8")
    return output_file
