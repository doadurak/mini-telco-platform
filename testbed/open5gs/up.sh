#!/usr/bin/env bash
# Start the Open5GS + UERANSIM testbed and attach NEF-QoS to its PCF.
set -euo pipefail
cd "$(dirname "$0")"

# NGAP (gNB <-> AMF) needs SCTP and the UPF/UEs need TUN; the WSL2/Docker Desktop
# kernel ships both as modules that are not loaded by default.
docker run --rm --privileged --pid=host alpine:3 nsenter -t 1 -m -u -n -i sh -c 'modprobe sctp && modprobe tun'

# The one-shot provisioning container keeps a stale bind mount across Docker restarts:
# remove it so it is recreated, then restart the UEs once subscribers exist.
docker compose rm -sf provision >/dev/null 2>&1 || true
docker compose up -d
until [[ "$(docker inspect -f '{{.State.Status}}' o5g-provision 2>/dev/null)" == "exited" ]]; do sleep 1; done
docker logs o5g-provision 2>&1 | grep provisioned || true
docker restart ues >/dev/null

echo "Waiting for UE PDU sessions..."
for tun in uesimtun0 uesimtun1 uesimtun2; do
  for _ in $(seq 1 60); do
    if docker exec ues ip -4 addr show "$tun" >/dev/null 2>&1; then
      echo "  $tun: $(docker exec ues ip -4 -o addr show "$tun" | awk '{print $4}')"
      break
    fi
    sleep 2
  done
done
