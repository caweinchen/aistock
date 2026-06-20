# AIStock Backend

FastAPI backend for the AIStock mobile app.

## Run

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:DB_PASSWORD = "your_mysql_password"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Default database settings are `DB_HOST=127.0.0.1`, `DB_PORT=3306`, `DB_USERNAME=aistock`, and `DB_NAME=at_stock`.
Set `DB_PASSWORD` before starting the API or running `backend/check_mysql.py`.

## Endpoints

- `GET /health`
- `GET /api/stocks`
- `GET /api/stocks/search?q=keyword`
- `GET /api/watchlist`
- `POST /api/watchlist/{code}`
- `DELETE /api/watchlist/{code}`
- `GET /api/stocks/{code}`
- `GET /api/stocks/{code}/factors`
- `GET /api/stocks/{code}/strategies`
- `GET /api/stocks/{code}/strategies/{strategy_id}`
- `GET /api/stocks/{code}/alerts`
- `GET /api/stocks/{code}/history`

The mobile app should call `GET /api/stocks` for the watchlist. When a user selects a stock, call `GET /api/stocks/{code}` and bind the lower detail panels to the returned `history`, `factors`, `strategies`, `alerts`, and `ai_summary`. When a user expands a strategy card, call `GET /api/stocks/{code}/strategies/{strategy_id}`.

Current data is mock data. Replace `STOCKS` in `backend/app/main.py` with database or TuShare-backed services when the data pipeline is ready.
