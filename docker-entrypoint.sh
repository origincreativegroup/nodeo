#!/bin/bash
set -e

echo "🔄 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed"
    exit 1
fi

echo "🚀 Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8002
