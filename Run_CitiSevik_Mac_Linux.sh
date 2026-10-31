#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/app/backend"
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
