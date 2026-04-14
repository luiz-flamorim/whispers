"""chain_log.py — accumulates per-hop data in memory and writes a CSV at end of run."""

import csv
import datetime
from pathlib import Path

_rows: list[dict] = []
_FIELDNAMES = ["time", "relay", "order", "received", "sent"]


def add_hop(order: int, relay: str, received: str, sent: str) -> None:
    """Record one hop. Timestamp is captured at call time (moment of receipt)."""
    _rows.append({
        "time":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "relay":    relay,
        "order":    order,
        "received": received,
        "sent":     sent,
    })


def save_csv(output_dir: str | Path | None = None) -> Path:
    """Write all accumulated rows to a timestamped CSV and return its path.

    Parameters
    ----------
    output_dir:
        Directory to write into. Defaults to the project root
        (two levels above this file: src/ → project root).
    """
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent.parent / "logs"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"chain_{timestamp}.csv"

    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(_rows)

    return filepath
