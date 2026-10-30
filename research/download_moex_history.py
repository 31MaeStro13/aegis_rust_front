"""Download and cache validated historical MOEX market data."""

import logging
import sys
from pathlib import Path

from research.src.market_data import fetch_history, save_history_cache


START_DATE = "2023-10-01"
END_DATE = "2026-10-18"
CACHE_DIR = Path("research/data/cache")

SECURITIES = [
    ("GAZP", "shares", "TQBR"),
    ("LKOH", "shares", "TQBR"),
    ("SU26238RMFS4", "bonds", "TQOB"),
    ("SU29014RMFS6", "bonds", "TQOB"),
    ("LQDT", "shares", "TQBR"),
    ("TGLD", "shares", "TQBR"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Download each configured security and save its history."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    failed_securities = []

    for security, market, board in SECURITIES:
        logger.info("Downloading %s / %s", security, board)

        try:
            df = fetch_history(
                security,
                market,
                START_DATE,
                END_DATE,
                board=board,
            )

            if df.empty:
                logger.error(
                    "No history returned for %s / %s; no file saved",
                    security,
                    board,
                )
                failed_securities.append(f"{security} / {board}")
                continue

            logger.info("Downloaded rows: %d", len(df))
            logger.info(
                "Date range: %s to %s",
                df["TRADEDATE"].min(),
                df["TRADEDATE"].max(),
            )

            output_path = save_history_cache(
                df,
                security,
                cache_dir=CACHE_DIR,
                board=board,
                market=market,
            )

            logger.info("Saved: %s", output_path.resolve())

        except Exception:
            failed_securities.append(f"{security} / {board}")
            logger.exception("MOEX fetch failed")

    if failed_securities:
        logger.error(
            "Download process finished with failures: %s",
            ", ".join(failed_securities),
        )
        return 1

    logger.info("Download process finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
