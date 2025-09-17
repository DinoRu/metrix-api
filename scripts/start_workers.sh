#!/usr/bin/env bash
set -euo pipefail

echo "Starting Celery stack..."

# --- Localisation du projet ---
# SCRIPT_DIR = meter_sync_api/scripts
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
# PROJECT_ROOT = meter_sync_api/
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." &>/dev/null && pwd)"

# Si ton package est directement ${PROJECT_ROOT}/app, laisse APP_PKG="app"
# Si ta structure est ${PROJECT_ROOT}/meter_sync_api/app, mets APP_PKG="meter_sync_api.app"
APP_PKG="${APP_PKG:-app}"  # surcharge possible depuis l'environnement

# --- Venv (optionnel) ---
if [[ -d "${PROJECT_ROOT}/.venv" ]]; then
  source "${PROJECT_ROOT}/.venv/bin/activate"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
  echo "Using existing virtualenv: ${VIRTUAL_ENV}"
else
  echo "⚠️  No virtualenv detected. Make sure dependencies are installed globally."
fi

# --- Répertoire de travail & PYTHONPATH ---
cd "${PROJECT_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# Vérification import
python - <<PY
import importlib, sys
m = "${APP_PKG}".split(".")[0]
try:
    importlib.import_module(m)
    print(f"✅ Python can import top-level package: {m}")
except Exception as e:
    print(f"❌ Cannot import package '{m}' from {sys.path[0]}.\n{e}")
    sys.exit(1)
PY

# --- Options communes Celery ---
APP_ARG="-A ${APP_PKG}.core.celery_app"
LOGLEVEL="${LOGLEVEL:-info}"

# --- Workers ---
echo "Starting Celery workers..."
celery ${APP_ARG} worker \
  --loglevel="${LOGLEVEL}" \
  --concurrency=4 \
  --hostname=worker-imports@%h \
  --queues=imports \
  --max-tasks-per-child=100 &

celery ${APP_ARG} worker \
  --loglevel="${LOGLEVEL}" \
  --concurrency=2 \
  --hostname=worker-exports@%h \
  --queues=exports \
  --max-tasks-per-child=50 &

celery ${APP_ARG} worker \
  --loglevel="${LOGLEVEL}" \
  --concurrency=4 \
  --hostname=worker-sync@%h \
  --queues=sync \
  --max-tasks-per-child=200 &

# --- Beat ---
echo "Starting Celery Beat..."
celery ${APP_ARG} beat --loglevel="${LOGLEVEL}" &

# --- Flower ---
echo "Starting Flower..."
celery ${APP_ARG} flower --port="${FLOWER_PORT:-5555}" &

wait
