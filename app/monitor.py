from __future__ import annotations
from datetime import datetime, timezone
from .db import connect, row, rows
from .notifications import send_push
from .retailers import CHECKERS


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


async def check_item(item_id: int) -> dict:
    item = row("SELECT * FROM watch_items WHERE id=?", (item_id,))
    if not item:
        raise KeyError("Watch item not found")

    checker = CHECKERS.get(item["retailer"], CHECKERS["other"])
    result = await checker.check(item["url"])
    old_status = item["last_status"]
    effective_status = result.status

    # A max-price rule can suppress an otherwise in-stock alert.
    price_ok = item["max_price"] is None or result.price is None or result.price <= item["max_price"]

    with connect() as con:
        con.execute(
            "UPDATE watch_items SET last_status=?, last_price=?, last_checked=?, last_error=? WHERE id=?",
            (result.status, result.price, utcnow(), None if result.status != "UNKNOWN" else result.reason, item_id),
        )
        if old_status != effective_status:
            con.execute(
                "INSERT INTO stock_events(item_id, old_status, new_status, price) VALUES(?,?,?,?)",
                (item_id, old_status, effective_status, result.price),
            )
        con.commit()

    # Alert on transition into stock, not on every poll.
    if effective_status == "IN_STOCK" and old_status != "IN_STOCK" and price_ok:
        price = f" — ${result.price:.2f}" if result.price is not None else ""
        send_push(
            f"IN STOCK: {item['name']}",
            f"{item['retailer'].title()}{price}. Tap to open product.",
            item["url"],
        )

    return {
        "id": item_id,
        "status": result.status,
        "price": result.price,
        "reason": result.reason,
        "alerted": effective_status == "IN_STOCK" and old_status != "IN_STOCK" and price_ok,
    }


async def check_due_items() -> None:
    # Scheduler runs once per minute. Interval is enforced using elapsed time in SQLite-compatible Python logic.
    now = datetime.now(timezone.utc)
    for item in rows("SELECT * FROM watch_items WHERE enabled=1"):
        due = True
        if item["last_checked"]:
            try:
                last = datetime.fromisoformat(item["last_checked"])
                due = (now - last).total_seconds() >= item["interval_seconds"]
            except ValueError:
                due = True
        if due:
            await check_item(item["id"])
