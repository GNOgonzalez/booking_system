#!/usr/bin/env bash
# Dump the Postgres database pointed at by DATABASE_URL into backups/.
#
# Usage:
#   ./scripts/backup_db.sh              # custom-format dump (default)
#   ./scripts/backup_db.sh --sql        # plain SQL instead (readable, larger)
#   ./scripts/backup_db.sh --keep 14    # delete dumps older than N days after success
#
# Requires: pg_dump at least as new as the server (Supabase is currently 17.x).
#   brew upgrade libpq && brew link --force libpq
# Override the binary with PG_DUMP=/path/to/pg_dump if needed.
#
# Supabase Free has no managed backups — run this daily (cron / launchd).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FORMAT=custom
KEEP_DAYS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sql) FORMAT=plain; shift ;;
    --keep)
      KEEP_DAYS="${2:?--keep requires a day count}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

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
  echo "DATABASE_URL is not set. Add it to .env (see .env.example)." >&2
  exit 1
fi

PG_DUMP_BIN="${PG_DUMP:-}"
if [[ -z "$PG_DUMP_BIN" ]]; then
  for candidate in \
    /opt/homebrew/opt/libpq/bin/pg_dump \
    /usr/local/opt/libpq/bin/pg_dump \
    "$(command -v pg_dump || true)"
  do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      PG_DUMP_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$PG_DUMP_BIN" || ! -x "$PG_DUMP_BIN" ]]; then
  echo "pg_dump not found. On macOS: brew install libpq && brew link --force libpq" >&2
  exit 1
fi

mkdir -p backups
STAMP="$(date +%Y-%m-%d_%H%M%S)"
HOST="$(python3 - <<'PY' "$DATABASE_URL"
import sys
from urllib.parse import urlparse
print(urlparse(sys.argv[1]).hostname or "db")
PY
)"

if [[ "$FORMAT" == "plain" ]]; then
  OUT="backups/${STAMP}_${HOST}.sql"
else
  OUT="backups/${STAMP}_${HOST}.dump"
fi
TMP="${OUT}.partial"

cleanup_partial() {
  rm -f "$TMP"
}
trap cleanup_partial EXIT

set +e
if [[ "$FORMAT" == "plain" ]]; then
  DUMP_ERR="$("$PG_DUMP_BIN" "$DATABASE_URL" \
    --format=plain \
    --no-owner \
    --no-acl \
    --file="$TMP" 2>&1)"
  DUMP_RC=$?
else
  DUMP_ERR="$("$PG_DUMP_BIN" "$DATABASE_URL" \
    --format=custom \
    --no-owner \
    --no-acl \
    --file="$TMP" 2>&1)"
  DUMP_RC=$?
fi
set -e

if [[ $DUMP_RC -ne 0 ]]; then
  echo "$DUMP_ERR" >&2
  if echo "$DUMP_ERR" | grep -qi 'server version mismatch'; then
    echo >&2
    echo "Your pg_dump is older than Supabase Postgres." >&2
    echo "  using: $PG_DUMP_BIN ($("$PG_DUMP_BIN" --version 2>/dev/null || true))" >&2
    echo "Fix:    brew upgrade libpq && brew link --force libpq" >&2
    echo "Or set: PG_DUMP=/path/to/pg_dump-17+ ./scripts/backup_db.sh" >&2
  fi
  exit "$DUMP_RC"
fi

mv "$TMP" "$OUT"
trap - EXIT

BYTES="$(wc -c <"$OUT" | tr -d ' ')"
echo "Wrote $OUT ($BYTES bytes) via $PG_DUMP_BIN"

if [[ -n "$KEEP_DAYS" ]]; then
  find backups -type f \( -name '*.dump' -o -name '*.sql' \) -mtime "+$KEEP_DAYS" -print -delete \
    | sed 's/^/Deleted old: /' || true
fi
