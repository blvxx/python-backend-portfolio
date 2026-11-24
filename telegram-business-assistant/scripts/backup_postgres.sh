#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must point to the source PostgreSQL database}"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
destination=${1:-"backups/assistant-${timestamp}.dump"}
mkdir -p "$(dirname "$destination")"
umask 077

pg_dump --format=custom --no-owner --no-acl --file="$destination" "$DATABASE_URL"
pg_restore --list "$destination" >/dev/null
sha256sum "$destination"
printf 'Backup verified: %s\n' "$destination"
