#!/usr/bin/env bash
# EC2 k3s: build images (optional), apply manifests, rollout.
#
# Usage (on EC2):
#   cd ~/fitlio && bash scripts/deploy_k8s.sh
#   BUILD_IMAGES=1 bash scripts/deploy_k8s.sh   # rebuild api + web images
#
# Requires: k3s, docker, kubectl (KUBECONFIG=/etc/rancher/k3s/k3s.yaml)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"

API_IMAGE="${FITLIO_API_IMAGE:-jayjuhoonchoi/fitlio:latest}"
WEB_IMAGE="${FITLIO_WEB_IMAGE:-jayjuhoonchoi/fitlio-web:latest}"

import_image() {
  local tag="$1"
  echo "[fitlio-k8s] import → k3s: ${tag}"
  docker save "${tag}" | sudo k3s ctr images import -
}

if [[ "${BUILD_IMAGES:-1}" == "1" ]]; then
  echo "[fitlio-k8s] building API image: ${API_IMAGE}"
  docker build -t "${API_IMAGE}" "${ROOT}"

  echo "[fitlio-k8s] building web image: ${WEB_IMAGE}"
  docker build -t "${WEB_IMAGE}" "${ROOT}/frontend-next"

  import_image "${API_IMAGE}"
  import_image "${WEB_IMAGE}"
fi

echo "[fitlio-k8s] applying manifests"
kubectl apply -f "${ROOT}/k8s/postgres.yaml"
kubectl apply -f "${ROOT}/k8s/api.yaml"
kubectl apply -f "${ROOT}/k8s/web.yaml"
kubectl apply -f "${ROOT}/k8s/ingress.yaml"

echo "[fitlio-k8s] rollout"
kubectl rollout restart deployment/api -n fitlio
kubectl rollout restart deployment/web -n fitlio
kubectl rollout status deployment/api -n fitlio --timeout=300s
kubectl rollout status deployment/web -n fitlio --timeout=300s

echo "[fitlio-k8s] pods"
kubectl get pods -n fitlio -o wide

echo "[fitlio-k8s] health (in-cluster api)"
kubectl run fitlio-curl-check --rm -i --restart=Never -n fitlio \
  --image=curlimages/curl:8.5.0 -- \
  curl -fsS "http://api:8000/health" || true

echo "[fitlio-k8s] done"
