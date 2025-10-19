#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME=${IMAGE_NAME:-devguardian-api}
IMAGE_TAG=${IMAGE_TAG:-latest}
REGISTRY=${REGISTRY:-}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

pushd "${PROJECT_ROOT}" >/dev/null

docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

if [[ -n "${REGISTRY}" ]]; then
  docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
  docker push "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
fi

popd >/dev/null

echo "Built image ${IMAGE_NAME}:${IMAGE_TAG}"
