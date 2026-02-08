#!/bin/bash
# Backup PostgreSQL database

set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/buyout_bot_$DATE.sql"

mkdir -p $BACKUP_DIR

echo "🔄 Creating backup..."
docker-compose exec -T postgres pg_dump -U postgres buyout_bot > $BACKUP_FILE

echo "✅ Backup created: $BACKUP_FILE"
echo "📦 Size: $(du -h $BACKUP_FILE | cut -f1)"

# Keep only last 7 backups
ls -t $BACKUP_DIR/*.sql | tail -n +8 | xargs -r rm
echo "🧹 Old backups cleaned up (keeping last 7)"
