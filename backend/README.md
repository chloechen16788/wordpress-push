# Press Flow Backend

FastAPI + SQLite backend for the automatic news rewriting and distribution system.

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Core APIs

- `POST /api/tasks/run-test`: trigger one manual fetch + rewrite batch
- `GET /api/batches?task_id=1`: list batches
- `GET /api/batches/{batch_id}/records`: list dual-pane records
- `POST /api/publish/batch`: batch publish
- `GET /api/stream?task_id=1&batch_id=1`: SSE progress stream

