from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a consistent SQLite backup.")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()

    args.target.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(args.source)
    try:
        target = sqlite3.connect(args.target)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    print(args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
