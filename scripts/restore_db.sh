#!/usr/bin/env bash
# Restore a dump created by scripts/backup_db.sh into DATABASE_URL.
#
# Usage:
#   ./scripts/restore_db.sh backups/2026-08-27_103000_….dump
#
# WARNING: this drops and recreates objects from the dump in the target database.
# Type the target hostname when prompted. Prefer restoring into a fresh / staging
# database first — never practise on production.
#
# pg_restore must match the dump format (same libpq as backup_db.sh).
#   brew upgrade libpq && brew link --force libpq

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "Usage: $0 path/to/backup.dump" >&2
  echo "Available dumps:" >&2
  ls -1t backups/*.{dump,sql} 2>/dev/null || echo "  (none in backups/)" >&2
  exit 1
fi

load_database_url() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    return 0
  fi
  if [[ ! -f .env ]]; then
    return 1
  fi
  DATABASE_URL="$(python3 - <<'PY'
from pathlib import Path
for raw in Path(".env").read_text().splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, value = line.partition("=")
    if key.strip() != "DATABASE_URL":
        continue
    value = value.strip()
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        value = value[1:-1]
    print(value)
    break
PY
)"
  export DATABASE_URL
  [[ -n "${DATABASE_URL}" ]]
}

if ! load_database_url; then
  echo "DATABASE_URL is not set." >&2
  exit 1
fi

HOST="$(python3 - <<'PY' "$DATABASE_URL"
import sys
from urllib.parse import urlparse
print(urlparse(sys.argv[1]).hostname or "")
PY
)"

resolve_bin() {
  local name="$1"
  local override="${2:-}"
  if [[ -n "$override" && -x "$override" ]]; then
    echo "$override"
    return 0
  fi
  for candidate in \
    "/opt/homebrew/opt/libpq/bin/$name" \
    "/usr/local/opt/libpq/bin/$name" \
    "$(command -v "$name" || true)"
  do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

echo "About to restore:"
echo "  dump:   $DUMP"
echo "  target: $HOST"
echo
read -r -p "Type the hostname ($HOST) to confirm: " CONFIRM
if [[ "$CONFIRM" != "$HOST" ]]; then
  echo "Aborted — hostname did not match." >&2
  exit 1
fi

case "$DUMP" in
  *.sql)
    if ! PSQL_BIN="$(resolve_bin psql "${PSQL:-}")"; then
      echo "psql not found. On macOS: brew install libpq && brew link --force libpq" >&2
      exit 1
    fi
    "$PSQL_BIN" "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$DUMP"
    ;;
  *.dump)
    if ! PG_RESTORE_BIN="$(resolve_bin pg_restore "${PG_RESTORE:-}")"; then
      echo "pg_restore not found. On macOS: brew install libpq && brew link --force libpq" >&2
      exit 1
    fi
    # --clean --if-exists drops objects before recreating them.
    # --no-owner --no-acl ignore role differences between local and Supabase.
    "$PG_RESTORE_BIN" \
      --dbname="$DATABASE_URL" \
      --clean \
      --if-exists \
      --no-owner \
      --no-acl \
      --verbose \
      "$DUMP"
    ;;
  *)
    echo "Unrecognized dump type (use .dump or .sql): $DUMP" >&2
    exit 1
    ;;
esac

echo "Restore finished."
