#!/usr/bin/env bash
# make executable: chmod +x run.sh
UVICORN_ARGS="--host 0.0.0.0 --port 8000 --reload"
python -m uvicorn app.main:app $UVICORN_ARGS
