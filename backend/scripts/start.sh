#!/bin/bash
echo "=== Margó startup ==="
echo "Running database migrations..."
if python -m alembic upgrade head 2>&1; then
    echo "Migrations complete."
else
    echo "WARNING: Migration failed, starting anyway..."
fi
echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
