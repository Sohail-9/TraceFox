#!/usr/bin/env bash
set -euo pipefail

export KRUTRIM_MODEL=${KRUTRIM_MODEL:-Krutrim-DeepSeek-R1}
export KRUTRIM_API_BASE_URL=${KRUTRIM_API_BASE_URL:-https://api.krutrim.com/v1}
export DEEPSEEK_ROUTER_MODEL=${DEEPSEEK_ROUTER_MODEL:-deepseek-r1}

uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000 --reload
