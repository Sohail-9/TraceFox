#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export TRACEFOX_ENVIRONMENT=${TRACEFOX_ENVIRONMENT:-local}

# Keep the uvicorn host/port in sync with TRACEFOX_* config so curls/redirects hit the right place.
UVICORN_HOST=${TRACEFOX_API_GATEWAY__HOST:-0.0.0.0}
UVICORN_PORT=${TRACEFOX_API_GATEWAY__PORT:-8000}

pushd "${PROJECT_ROOT}" >/dev/null
uvicorn services.api_gateway.main:app --host "${UVICORN_HOST}" --port "${UVICORN_PORT}" --reload
popd >/dev/null
