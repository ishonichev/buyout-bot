#!/bin/bash
# Script to initialize database with Alembic migrations

set -e

echo "🔄 Waiting for PostgreSQL to be ready..."
while ! docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    sleep 1
done

echo "✅ PostgreSQL is ready"

echo "🔄 Running Alembic migrations..."
docker-compose exec -T bot alembic upgrade head

echo "✅ Database initialized successfully!"
echo ""
echo "🎉 You can now use the bot!"
echo "   Test it: /start"
echo "   Admin panel: /admin"
