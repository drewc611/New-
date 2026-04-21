#!/usr/bin/env bash
# Install AMIE onto a Kubernetes cluster using Helm.
#
# Usage:
#   scripts/helm-install.sh [release-name] [namespace]
#
# Examples:
#   scripts/helm-install.sh amie amie
#   LLM_PROVIDER=ollama scripts/helm-install.sh
#   LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... scripts/helm-install.sh

set -euo pipefail

RELEASE="${1:-amie}"
NAMESPACE="${2:-amie}"
PROVIDER="${LLM_PROVIDER:-mock}"

EXTRA_SETS=()
EXTRA_SETS+=("--set" "llm.provider=${PROVIDER}")

case "$PROVIDER" in
  anthropic)
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      echo "error: ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic" >&2
      exit 1
    fi
    EXTRA_SETS+=("--set" "llm.anthropicApiKey=${ANTHROPIC_API_KEY}")
    ;;
  ollama)
    EXTRA_SETS+=("--set" "ollama.enabled=true")
    ;;
  mock)
    ;;
  *)
    echo "error: unknown LLM_PROVIDER=${PROVIDER}" >&2
    exit 1
    ;;
esac

helm upgrade --install "$RELEASE" deploy/helm/usps-amie \
  --namespace "$NAMESPACE" --create-namespace \
  "${EXTRA_SETS[@]}" \
  --wait --timeout 5m

kubectl -n "$NAMESPACE" get pods -l "app.kubernetes.io/instance=${RELEASE}"
