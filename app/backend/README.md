# CitiSevik API

Run from `app/backend`:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

SQLite database is created automatically at first startup. Demo data is seeded once. Delete `citisevik.sqlite3` to reset the demo database.

This is a prototype. Role headers are a UI simulation, not authentication. Do not expose publicly with real personal data.
