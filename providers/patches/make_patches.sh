#!/usr/bin/env bash
# Maintainer tool: record our local changes to the NCSRD provider repositories as patches.
# The provider repos are git submodules pinned to an upstream commit; on a fresh clone,
# scripts/setup.sh applies these patches (ports, Docker networks, CAPIF hosts, the NEF
# Monitoring Event fixes and the compose files the upstream repos do not ship).
#
#   bash providers/patches/make_patches.sh
set -euo pipefail
cd "$(dirname "$0")/.."

make_patch() {  # repo  file...
  local repo=$1; shift
  local idx; idx=$(mktemp)
  # temporary index = HEAD + the listed files, so new files are included without touching the repo
  GIT_INDEX_FILE=$idx git -C "$repo" read-tree HEAD
  GIT_INDEX_FILE=$idx git -C "$repo" add -- "$@"
  GIT_INDEX_FILE=$idx git -C "$repo" diff --cached --binary HEAD > "patches/$repo.patch"
  rm -f "$idx"
  echo "patches/$repo.patch: $(grep -c '^diff --git' "patches/$repo.patch") files"
}

make_patch CamaraLocationRetrieval .env app/invoker_onboarding/invoker_config_sample.json docker-compose.yaml
make_patch NEF .env docker-compose.yaml docker-compose.auth.yaml \
  MonitoringEventAPI/app/dependencies.py \
  MonitoringEventAPI/app/provider_onboarding/provider_config_sample.json \
  MonitoringEventAPI/app/provider_onboarding/publish_openapi_service.py \
  MonitoringEventAPI/app/routers/monitoring_event.py \
  MonitoringEventAPI/app/services/monitoring_event_service.py \
  MonitoringEventAPI/app/utils/db_data_handler.py \
  init_db_setup/mongo-init.js
make_patch NEF-QoS docker-compose.yml
make_patch camara-QoD docker-compose.yaml quality_on_demand_openapi.json
