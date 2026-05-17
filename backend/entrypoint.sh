#!/bin/bash

echo "Waiting for database..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(os.environ['DATABASE_URL'])
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    sleep 1
done
echo "Database ready."

echo "Running Alembic migrations..."
if ! alembic upgrade head; then
    echo "Migration failed — resetting schema and retrying..."
    python - <<'EOF'
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.autocommit = True
cur = conn.cursor()
cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public;")
conn.close()
print("Schema reset complete.")
EOF
    if ! alembic upgrade head; then
        echo "Migration failed after schema reset. Aborting."
        exit 1
    fi
fi

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/app
