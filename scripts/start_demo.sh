#!/usr/bin/env bash
set -euo pipefail

OPENCAPIF_DIR="/home/turkad/OpenCAPIF/capif/services"
PROJECT_DIR="/home/turkad/mini-telco-platform"

echo "[1/4] Starting OpenCAPIF..."
cd "$OPENCAPIF_DIR"
./run.sh

echo "[2/4] Starting NEF provider stack..."
cd "$PROJECT_DIR/providers/NEF"
docker compose -f docker-compose.yaml -f docker-compose.auth.yaml up -d --build

echo "[3/4] Starting CAMARA Location Retrieval provider..."
cd "$PROJECT_DIR/providers/CamaraLocationRetrieval"
docker compose up -d --build

echo "[4/4] Starting mini telco orchestration platform..."
cd "$PROJECT_DIR"
docker compose -f docker-compose.capif.yml up -d --build

echo
echo "Demo stack is starting."
echo "Frontend:   http://localhost:8000/"
echo "Swagger:    http://localhost:8000/docs"
echo "Location:   http://localhost:8003/docs"
echo "NEF direct: http://localhost:9999/docs"
