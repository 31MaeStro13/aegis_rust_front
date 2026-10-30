from pathlib import Path
import time
import requests
import pandas as pd

BASE_URL = "https://iss.moex.com/iss"
START_DATE = "2023-10-01"
END_DATE = "2026-10-18"
PAGE_SIZE = 100
CACHE_DIR = Path("research/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

securities = [
    ("GAZP", "shares", "TQBR"),
    ("LKOH", "shares", "TQBR"),
    ("SU26238RMFS4", "bonds", "TQOB"),
    ("SU29014RMFS6", "bonds", "TQOB"),
    ("LQDT", "shares", "TQTF"),
    ("TGLD", "shares", "TQTF"),
]

session = requests.Session()

for security, market, board in securities:
    print(f"\n--- Downloading {security} / {board} ---")

    url = (
        f"{BASE_URL}/history/engines/stock/markets/{market}"
        f"/boards/{board}/securities/{security}.json"
    )

    all_pages = []
    start = 0
    expected_total = None

    try:
        while True:
            params = {
                "from": START_DATE,
                "till": END_DATE,
                "start": start,
                "iss.meta": "off",
                "iss.only": "history,history.cursor",
                "history.columns": "TRADEDATE,SECID,BOARDID,CLOSE",
            }

            response = session.get(url, params=params, timeout=45)
            response.raise_for_status()
            payload = response.json()

            history = payload.get("history", {})
            columns = history.get("columns", [])
            rows = history.get("data", [])

            cursor = payload.get("history.cursor", {})
            cursor_rows = cursor.get("data", [])
            cursor_columns = cursor.get("columns", [])

            if cursor_rows:
                cursor_data = dict(zip(cursor_columns, cursor_rows[0]))
                expected_total = cursor_data.get("TOTAL")

            if not rows:
                break

            page = pd.DataFrame(rows, columns=columns)
            all_pages.append(page)

            print(
                f"Page start={start}: {len(page)} rows; "
                f"downloaded so far={sum(len(x) for x in all_pages)}"
            )

            start += len(rows)

            if expected_total is not None and start >= int(expected_total):
                break

            time.sleep(0.2)

        if not all_pages:
            print("WARNING: No history returned; no file saved.")
            continue

        df = pd.concat(all_pages, ignore_index=True)
        df["TRADEDATE"] = pd.to_datetime(df["TRADEDATE"], errors="coerce")
        df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")
        df = df.sort_values("TRADEDATE").reset_index(drop=True)

        duplicate_dates = int(df["TRADEDATE"].duplicated().sum())
        missing_dates = int(df["TRADEDATE"].isna().sum())
        missing_closes = int(df["CLOSE"].isna().sum())
        nonpositive_closes = int((df["CLOSE"].dropna() <= 0).sum())

        print("Expected rows:", expected_total)
        print("Downloaded rows:", len(df))
        print("Date range:",
              df["TRADEDATE"].min(),
              "to",
              df["TRADEDATE"].max())
        print("Duplicate dates:", duplicate_dates)
        print("Invalid dates:", missing_dates)
        print("Missing closes:", missing_closes)
        print("Non-positive closes:", nonpositive_closes)

        filename = f"{security}_{board}_history.csv"
        output_path = CACHE_DIR / filename
        df.to_csv(output_path, index=False, date_format="%Y-%m-%d")
        print("Saved:", output_path.resolve())

    except Exception as exc:
        print("ERROR:", repr(exc))

print("\nDownload process finished.")
