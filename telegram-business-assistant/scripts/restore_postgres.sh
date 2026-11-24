#!/usr/bin/env sh
set -eu

backup=${1:?Usage: sh scripts/restore_postgres.sh BACKUP.dump}
: "${RESTORE_TARGET_DATABASE_URL:?Set RESTORE_TARGET_DATABASE_URL explicitly}"
: "${RESTORE_CONFIRM:?Set RESTORE_CONFIRM to I_UNDERSTAND_THIS_REPLACES_DATA}"

if [ "$RESTORE_CONFIRM" != "I_UNDERSTAND_THIS_REPLACES_DATA" ]; then
  echo "Restore confirmation did not match; refusing to modify the target database." >&2
  exit 2
fi

if [ ! -s "$backup" ]; then
  echo "Backup file is missing or empty: $backup" >&2
  exit 2
fi

pg_restore --list "$backup" >/dev/null
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --dbname="$RESTORE_TARGET_DATABASE_URL" \
  "$backup"

psql "$RESTORE_TARGET_DATABASE_URL" -v ON_ERROR_STOP=1 -Atc \
  "SELECT CASE WHEN to_regclass('public.leads') IS NOT NULL
              THEN 'restore schema verified' ELSE 'restore schema missing' END"
