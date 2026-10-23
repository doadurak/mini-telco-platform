#!/usr/bin/env bash
# One-time setup of the platform on a new machine (Ubuntu, natively or in WSL2).
# Safe to run again: every step checks what is already done.
#
#   git clone --recurse-submodules https://github.com/doadurak/mini-telco-platform.git
#   cd mini-telco-platform && bash scripts/setup.sh
#
# Afterwards: put your LLM API key(s) into .env, then run  bash scripts/demo_up.sh
set -euo pipefail
cd "$(dirname "$0")/.."

OPENCAPIF_HOME="${OPENCAPIF_HOME:-$HOME/OpenCAPIF}"
OPENCAPIF_REPO="https://labs.etsi.org/rep/ocf/capif.git"
OPENCAPIF_TAG="v4.0.0-release"          # the version the testbed was built and measured with
ok()   { echo -e "  \033[32m✔\033[0m $*"; }
fail() { echo -e "  \033[31m✘\033[0m $*"; exit 1; }

echo "1/6 Prerequisites"
for c in git docker python3 curl nc; do command -v $c >/dev/null || fail "$c is missing (see docs/SETUP_AND_USAGE.md, step 1)"; done
docker info >/dev/null 2>&1 || fail "Docker is installed but not running (start Docker Desktop / the docker service)"
docker compose version >/dev/null 2>&1 || fail "docker compose v2 is missing"
python3 -c 'import sys; assert sys.version_info >= (3, 10)' || fail "Python 3.10 or newer is needed"
python3 -m venv --help >/dev/null 2>&1 || fail "python3-venv is missing (sudo apt install python3-venv)"
mem_gb=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
[ "$mem_gb" -ge 12 ] && ok "tools present, ${mem_gb} GB RAM" || echo "  ! only ${mem_gb} GB RAM: the full stack needs about 10 GB"

echo "2/6 NCSRD provider repositories (git submodules) and our patches"
git submodule update --init providers/CamaraLocationRetrieval providers/NEF providers/NEF-QoS providers/camara-QoD
for r in CamaraLocationRetrieval NEF NEF-QoS camara-QoD; do
  p="providers/patches/$r.patch"
  if git -C "providers/$r" apply --check "../../$p" 2>/dev/null; then
    git -C "providers/$r" apply "../../$p"; ok "$r: patch applied"
  elif git -C "providers/$r" apply --reverse --check "../../$p" 2>/dev/null; then
    ok "$r: patch already applied"
  else
    fail "$r: $p does not apply (local changes in providers/$r?)"
  fi
done
mkdir -p providers/NEF/MonitoringEventAPI/app/provider_onboarding/provider_folder

echo "3/6 OpenCAPIF $OPENCAPIF_TAG (ETSI OCF) in $OPENCAPIF_HOME"
if [ -d "$OPENCAPIF_HOME/capif/services" ]; then
  ok "already present"
else
  mkdir -p "$OPENCAPIF_HOME"
  git clone --depth 1 --branch "$OPENCAPIF_TAG" "$OPENCAPIF_REPO" "$OPENCAPIF_HOME/capif"
  ok "cloned"
fi
[ "$OPENCAPIF_HOME" = "$HOME/OpenCAPIF" ] || echo "  ! non-default location: export OPENCAPIF_DIR=$OPENCAPIF_HOME/capif/services before start.sh"

echo "4/6 Python environment (venv) for the scripts"
[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt
ok "venv/ with $(venv/bin/python --version)"

echo "5/6 Configuration (.env)"
if [ -f .env ]; then
  ok ".env exists"
else
  cp .env.example .env
  ok ".env created from .env.example"
fi
if grep -qE '^(OPENAI|ANTHROPIC|GEMINI)_API_KEY=.+' .env; then
  ok "an LLM API key is set"
else
  echo "  ! no LLM API key in .env yet: add OPENAI_API_KEY (and optionally ANTHROPIC_API_KEY / GEMINI_API_KEY)"
fi

echo "6/6 Docker network"
docker network create capif-network >/dev/null 2>&1 && ok "capif-network created" || ok "capif-network exists"

echo
echo "Setup done. Next:"
echo "  1. make sure .env contains your LLM API key(s)"
echo "  2. bash scripts/demo_up.sh      (first run downloads the images: 15-30 minutes)"
