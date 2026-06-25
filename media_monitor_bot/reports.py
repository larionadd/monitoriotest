from __future__ import annotations

import csv
from pathlib import Path

from .db import Database


def write_csv_report(db: Database, chat_id: int, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"media-monitor-report-{chat_id}.csv"
    rows = db.report_rows(chat_id)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["надіслано", "ключ", "джерело", "заголовок", "дата_публікації", "url"])
        for row in rows:
            writer.writerow(
                [
                    row["sent_at"],
                    row["keyword"],
                    row["source"],
                    row["title"],
                    row["published_at"],
                    row["url"],
                ]
            )
    return path
