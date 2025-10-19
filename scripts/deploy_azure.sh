#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT=${ENVIRONMENT:-dev}
AZURE_LOCATION=${AZURE_LOCATION:-eastus}
TF_ACTION=${TF_ACTION:-apply}
TF_AUTO_APPROVE=${TF_AUTO_APPROVE:-true}
IMAGE=${IMAGE:?IMAGE environment variable must be set (registry/repository:tag).}
CPU=${CPU:-0.5}
MEMORY_GB=${MEMORY_GB:-1.0}
MIN_REPLICAS=${MIN_REPLICAS:-1}
MAX_REPLICAS=${MAX_REPLICAS:-3}
KRUTRIM_MODEL=${KRUTRIM_MODEL:-Krutrim-DeepSeek-R1}
KRUTRIM_API_BASE_URL=${KRUTRIM_API_BASE_URL:-https://api.krutrim.com/v1}
DEEPSEEK_ROUTER_MODEL=${DEEPSEEK_ROUTER_MODEL:-deepseek-r1}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${PROJECT_ROOT}/infrastructure/azure"

pushd "${INFRA_DIR}" >/dev/null

terraform init

CMD=(terraform "${TF_ACTION}" \
  -var="location=${AZURE_LOCATION}" \
  -var="environment=${ENVIRONMENT}" \
  -var="image=${IMAGE}" \
  -var="cpu=${CPU}" \
  -var="memory_gb=${MEMORY_GB}" \
  -var="min_replicas=${MIN_REPLICAS}" \
  -var="max_replicas=${MAX_REPLICAS}" \
  -var="krutrim_model=${KRUTRIM_MODEL}" \
  -var="krutrim_api_base_url=${KRUTRIM_API_BASE_URL}" \
  -var="deepseek_router_model=${DEEPSEEK_ROUTER_MODEL}")

if [[ "${TF_AUTO_APPROVE}" == "true" ]]; then
  CMD+=("-auto-approve")
fi

"${CMD[@]}"

popd >/dev/null

echo "Terraform ${TF_ACTION} completed for environment ${ENVIRONMENT} in ${AZURE_LOCATION}"
