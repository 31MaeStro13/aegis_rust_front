
"""MOEX ISS historical market-data retrieval, validation, and caching."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests


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
    import pandas as pd
    import requests

    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")
    if market not in {"shares", "index"}:
        raise ValueError("Invalid market; use 'shares' or 'index'")

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
        "history.columns": "TRADEDATE,SECID,BOARDID,CLOSE",
    }

    all_rows = []
    expected_columns = None
    expected_total = None
    start = 0
    pages_retrieved = 0

    session = requests.Session()
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
        return pd.DataFrame(
            columns=["TRADEDATE", "SECID", "CLOSE"]
        )

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

    if df["CLOSE"].isna().any():
        raise ValueError("MOEX history contains missing or invalid closes")

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

    clean_df = df.copy()
    clean_df["TRADEDATE"] = pd.to_datetime(
        clean_df["TRADEDATE"], errors="coerce"
    )

    if clean_df["TRADEDATE"].isna().any():
        raise ValueError("TRADEDATE contains invalid dates")

    if clean_df["TRADEDATE"].duplicated().any():
        raise ValueError("TRADEDATE contains duplicate dates")

    clean_df["CLOSE"] = pd.to_numeric(
        clean_df["CLOSE"], errors="coerce"
    )

    if clean_df["CLOSE"].isna().any():
        raise ValueError("CLOSE contains invalid prices")

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
