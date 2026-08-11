# Card Stock Alert — Render-ready MVP

Phone-friendly card inventory monitor for Target, Walmart, Topps, and generic product pages.

## Included

- FastAPI backend
- Installable PWA dashboard
- Web Push notifications
- Target/Walmart/Topps retailer modules
- SQLite watchlist and stock-event storage
- `render.yaml` for one-click Render Blueprint deployment
- Persistent-disk support through `DATA_DIR`
- `/api/health` health check

## Deploy on Render

See **DEPLOY_RENDER.md** for the step-by-step instructions.

## Local run

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows, activate with `.venv\\Scripts\\activate` instead.

## Data storage

Locally, the app stores data in the project directory. On Render, `render.yaml` sets `DATA_DIR=/var/data` and attaches a persistent disk there.

## Limitation

This project does not bypass retailer CAPTCHAs, queues, authentication, or anti-bot controls. When stock cannot be determined reliably, it reports `UNKNOWN`.
