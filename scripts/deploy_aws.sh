#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
TF_ACTION=${TF_ACTION:-apply}
TF_AUTO_APPROVE=${TF_AUTO_APPROVE:-true}
IMAGE=${IMAGE:?IMAGE environment variable must be set (registry/repository:tag).}
SUBNET_IDS=${SUBNET_IDS:?SUBNET_IDS environment variable must be set (JSON array).}
SG_IDS=${SG_IDS:?SG_IDS environment variable must be set (JSON array).}
CPU=${CPU:-512}
MEMORY=${MEMORY:-1024}
DESIRED_COUNT=${DESIRED_COUNT:-1}
KRUTRIM_MODEL=${KRUTRIM_MODEL:-Krutrim-DeepSeek-R1}
KRUTRIM_API_BASE_URL=${KRUTRIM_API_BASE_URL:-https://api.krutrim.com/v1}
DEEPSEEK_ROUTER_MODEL=${DEEPSEEK_ROUTER_MODEL:-deepseek-r1}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${PROJECT_ROOT}/infrastructure/aws"

pushd "${INFRA_DIR}" >/dev/null

terraform init

CMD=(terraform "${TF_ACTION}" \
  -var="region=${AWS_REGION}" \
  -var="environment=${ENVIRONMENT}" \
  -var="image=${IMAGE}" \
  -var="subnet_ids=${SUBNET_IDS}" \
  -var="security_group_ids=${SG_IDS}" \
  -var="cpu=${CPU}" \
  -var="memory=${MEMORY}" \
  -var="desired_count=${DESIRED_COUNT}" \
  -var="krutrim_model=${KRUTRIM_MODEL}" \
  -var="krutrim_api_base_url=${KRUTRIM_API_BASE_URL}" \
  -var="deepseek_router_model=${DEEPSEEK_ROUTER_MODEL}")

if [[ "${TF_AUTO_APPROVE}" == "true" ]]; then
  CMD+=("-auto-approve")
fi

"${CMD[@]}"

popd >/dev/null

echo "Terraform ${TF_ACTION} completed for environment ${ENVIRONMENT} in ${AWS_REGION}"
