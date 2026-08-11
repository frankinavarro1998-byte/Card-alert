from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "card_alert.db"


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS watch_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                retailer TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                max_price REAL,
                interval_seconds INTEGER NOT NULL DEFAULT 90,
                last_status TEXT NOT NULL DEFAULT 'UNKNOWN',
                last_price REAL,
                last_checked TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS stock_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                price REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(item_id) REFERENCES watch_items(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL UNIQUE,
                subscription_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute(query, params).fetchall()]


def row(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as con:
        r = con.execute(query, params).fetchone()
        return dict(r) if r else None


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with connect() as con:
        cur = con.execute(query, params)
        con.commit()
        return int(cur.lastrowid or 0)


def save_subscription(sub: dict[str, Any]) -> None:
    endpoint = sub["endpoint"]
    with connect() as con:
        con.execute(
            """INSERT INTO push_subscriptions(endpoint, subscription_json)
               VALUES(?, ?)
               ON CONFLICT(endpoint) DO UPDATE SET subscription_json=excluded.subscription_json""",
            (endpoint, json.dumps(sub)),
        )
        con.commit()
