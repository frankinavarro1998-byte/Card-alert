from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .db import init_db, rows, row, execute, connect, save_subscription
from .models import WatchItemCreate, WatchItemUpdate, PushSubscription
from .monitor import check_item, check_due_items
from .notifications import ensure_vapid_keys

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_vapid_keys()
    scheduler.add_job(check_due_items, "interval", seconds=60, max_instances=1, coalesce=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Card Stock Alert", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/manifest.json")
def manifest():
    return FileResponse(STATIC / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


@app.get("/api/watchlist")
def list_watchlist():
    return rows("SELECT * FROM watch_items ORDER BY id DESC")


@app.post("/api/watchlist")
def create_watch(item: WatchItemCreate):
    try:
        item_id = execute(
            "INSERT INTO watch_items(name,url,retailer,max_price,interval_seconds) VALUES(?,?,?,?,?)",
            (item.name, str(item.url), item.retailer, item.max_price, item.interval_seconds),
        )
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(409, "That product URL is already on your watchlist")
        raise
    return row("SELECT * FROM watch_items WHERE id=?", (item_id,))


@app.patch("/api/watchlist/{item_id}")
def update_watch(item_id: int, patch: WatchItemUpdate):
    current = row("SELECT * FROM watch_items WHERE id=?", (item_id,))
    if not current:
        raise HTTPException(404, "Watch item not found")
    data = patch.model_dump(exclude_unset=True)
    if not data:
        return current
    fields, values = [], []
    for k, v in data.items():
        fields.append(f"{k}=?")
        values.append(int(v) if k == "enabled" else v)
    values.append(item_id)
    with connect() as con:
        con.execute(f"UPDATE watch_items SET {', '.join(fields)} WHERE id=?", tuple(values))
        con.commit()
    return row("SELECT * FROM watch_items WHERE id=?", (item_id,))


@app.delete("/api/watchlist/{item_id}")
def delete_watch(item_id: int):
    with connect() as con:
        con.execute("DELETE FROM stock_events WHERE item_id=?", (item_id,))
        cur = con.execute("DELETE FROM watch_items WHERE id=?", (item_id,))
        con.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Watch item not found")
    return {"ok": True}


@app.post("/api/check/{item_id}")
async def check_now(item_id: int):
    try:
        return await check_item(item_id)
    except KeyError:
        raise HTTPException(404, "Watch item not found")


@app.post("/api/check-all")
async def check_all():
    results = []
    for item in rows("SELECT id FROM watch_items WHERE enabled=1"):
        results.append(await check_item(item["id"]))
    return results


@app.get("/api/events")
def events():
    return rows(
        """SELECT e.*, w.name, w.retailer, w.url
           FROM stock_events e JOIN watch_items w ON w.id=e.item_id
           ORDER BY e.id DESC LIMIT 100"""
    )


@app.get("/api/push/public-key")
def push_public_key():
    return {"publicKey": ensure_vapid_keys()}


@app.post("/api/push/subscribe")
def push_subscribe(sub: PushSubscription):
    save_subscription(sub.model_dump())
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True, "service": "card-stock-alert"}
