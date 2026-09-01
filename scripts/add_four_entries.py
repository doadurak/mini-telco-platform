import json
from pathlib import Path
from collections import Counter

ALL_QOS = ["QOS_E","QOS_S","QOS_M","QOS_L","QOS_E_STREAMING","QOS_GAMING","QOS_LOW_LATENCY","QOS_CRITICAL_COMMS"]

extra = [
    {
        "id": "profile_en_025",
        "intent": "List all QoS tiers for +12025550180 before provisioning a long-term policy",
        "language": "en", "difficulty": "medium", "category": "qos_profiles",
        "source": "synthetic",
        "expected": {"service_id": "qos-profiles", "operation_id": "retrieveQoSProfiles", "method": "POST"},
        "payload_checks": {"required_fields": [], "device.phoneNumber_if_present": "+12025550180"}
    },
    {
        "id": "profile_tr_025",
        "intent": "Uzun vadeli politika hazırlamadan önce +12025550180 için tüm QoS katmanlarını listele",
        "language": "tr", "difficulty": "medium", "category": "qos_profiles",
        "source": "synthetic (Turkish)",
        "expected": {"service_id": "qos-profiles", "operation_id": "retrieveQoSProfiles", "method": "POST"},
        "payload_checks": {"required_fields": [], "device.phoneNumber_if_present": "+12025550180"}
    },
    {
        "id": "prov_en_025",
        "intent": "Permanently configure the best available QoS for +306912345678 used in smart grid telemetry",
        "language": "en", "difficulty": "hard", "category": "qos_provisioning",
        "source": "synthetic",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile"], "device.phoneNumber": "+306912345678", "qosProfile_valid": ALL_QOS}
    },
    {
        "id": "prov_tr_025",
        "intent": "Akıllı şebeke telemetrisi için kullanılan +306912345678 için mevcut en iyi QoS kalıcı olarak yapılandır",
        "language": "tr", "difficulty": "hard", "category": "qos_provisioning",
        "source": "synthetic (Turkish)",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile"], "device.phoneNumber": "+306912345678", "qosProfile_valid": ALL_QOS}
    },
]

GT_PATH = Path(__file__).parent.parent / "datasets" / "ground_truth.json"
data = json.loads(GT_PATH.read_text(encoding="utf-8"))
existing_ids = {e["id"] for e in data["entries"]}

added = 0
for e in extra:
    if e["id"] not in existing_ids:
        data["entries"].append(e)
        added += 1

total = len(data["entries"])
data["_meta"]["total_entries"] = total
dist = Counter(e["category"] for e in data["entries"])
data["_meta"]["service_distribution"] = {
    "qod": dist.get("qod_session", 0),
    "qos-profiles": dist.get("qos_profiles", 0),
    "qos-provisioning": dist.get("qos_provisioning", 0),
    "location-retrieval": dist.get("location_retrieval", 0),
    "edge_cases": dist.get("edge_case", 0),
}
GT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
ids = [e["id"] for e in data["entries"]]
assert len(ids) == len(set(ids)), "Duplicate IDs!"
print(f"Added {added}, total: {total}")
print("Distribution:", data["_meta"]["service_distribution"])
print("ID check: OK")
