"""Quick RAG Context Engine test — run with: venv/bin/python test_rag.py"""
import json
from backend.rag_context import get_rag_metadata, get_all_services_summary, get_payload_schema_prompt

meta = get_rag_metadata()
print("=== RAG Metadata ===")
print(json.dumps(meta, indent=2))

summaries = get_all_services_summary()
print("\n=== Service Summaries ===")
for s in summaries:
    print(f"  {s['service_id']}: {len(s['operations'])} operation(s), base_path={s['base_path']}")

print("\n=== QoD createSession Schema Context ===")
ctx = get_payload_schema_prompt("qod", "createSession")
print(ctx[:2000])

print("\n=== location-retrieval retrieveLocation ===")
ctx2 = get_payload_schema_prompt("location-retrieval", "retrieveLocation")
print(ctx2[:1000])
