#!/bin/bash
set -e

echo "🚀 Starting application..."
# Note: Migrations temporarily skipped due to broken migration chain
# All required schema changes have been applied manually
exec uvicorn main:app --host 0.0.0.0 --port 8002
