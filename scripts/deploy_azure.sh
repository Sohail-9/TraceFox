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
  -var="max_replicas=${MAX_REPLICAS}")

if [[ "${TF_AUTO_APPROVE}" == "true" ]]; then
  CMD+=("-auto-approve")
fi

"${CMD[@]}"

popd >/dev/null

echo "TraceFox deployment (${TF_ACTION}) completed for environment ${ENVIRONMENT} in ${AZURE_LOCATION}"
