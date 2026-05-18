#!/usr/bin/env bash
# Shared docker compose file list for Fitlio (standard vs k8s alt ports).
# shellcheck shell=bash
#
# Usage (from other scripts after sourcing PROJECT_DIR):
#   source "${SCRIPT_DIR}/_fitlio_compose.sh"
#   fitlio_compose_set_args "$PROJECT_DIR"
#   docker compose "${FITLIO_COMPOSE_ARGS[@]}" up -d
#
# Selection order:
#   1. FITLIO_USE_K8S_ALT_PORTS=1
#   2. Marker file ${PROJECT_DIR}/.fitlio-k8s-alt-ports exists
#   3. FITLIO_HTTPS_VERIFY_PORT set and not 443 (sync with fix_https.sh)
#
fitlio_compose_set_args() {
  local project_dir="${1:?project dir}"
  local verify_port="${FITLIO_HTTPS_VERIFY_PORT:-443}"
  local use_alt=0

  if [[ "${FITLIO_USE_K8S_ALT_PORTS:-0}" == "1" ]]; then
    use_alt=1
  elif [[ -f "${project_dir}/.fitlio-k8s-alt-ports" ]]; then
    use_alt=1
  elif [[ -n "${FITLIO_HTTPS_VERIFY_PORT:-}" && "${verify_port}" != "443" ]]; then
    use_alt=1
  fi

  if [[ "${use_alt}" -eq 1 ]]; then
    FITLIO_COMPOSE_USE_ALT=1
    FITLIO_COMPOSE_ARGS=( -f docker-compose.yml -f docker-compose.k8s-alt-ports.yml )
  else
    FITLIO_COMPOSE_USE_ALT=0
    FITLIO_COMPOSE_ARGS=( -f docker-compose.yml )
  fi
}

fitlio_compose_sync_marker() {
  local project_dir="${1:?project dir}"
  local use_alt="${2:?0 or 1}"

  if [[ "${use_alt}" -eq 1 ]]; then
    : >"${project_dir}/.fitlio-k8s-alt-ports"
  else
    rm -f "${project_dir}/.fitlio-k8s-alt-ports"
  fi
}
