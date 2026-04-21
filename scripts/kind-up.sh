#!/usr/bin/env bash
# Stand up a local kind cluster, build AMIE images, load them, install via Helm.
#
# Requires: docker, kind, helm, kubectl on PATH.

set -euo pipefail

CLUSTER="${CLUSTER:-amie}"
TAG="${TAG:-0.1.0}"

if ! kind get clusters | grep -q "^${CLUSTER}$"; then
  kind create cluster --name "$CLUSTER"
fi

docker build -t "usps-amie-backend:${TAG}" -f deploy/docker/backend.Dockerfile .
docker build -t "usps-amie-frontend:${TAG}" -f deploy/docker/frontend.Dockerfile --target prod .

kind load docker-image "usps-amie-backend:${TAG}" --name "$CLUSTER"
kind load docker-image "usps-amie-frontend:${TAG}" --name "$CLUSTER"

helm upgrade --install amie deploy/helm/usps-amie \
  --namespace amie --create-namespace \
  --set backend.image.tag="${TAG}" \
  --set frontend.image.tag="${TAG}" \
  --wait --timeout 5m

echo
echo "AMIE is running on kind. Port forward to reach it:"
echo "  kubectl port-forward -n amie svc/amie-frontend 8080:80"
echo "  open http://localhost:8080"
