"""
Device identifier resolution: MSISDN -> UE IPv4 from the 5GC subscriber DB.

CAMARA requests usually identify a device only by phoneNumber, but the PCF
(Npcf_PolicyAuthorization) binds an AF session to the UE's PDU session by
its IP address. The southbound adapter therefore resolves the phone number
against the Open5GS subscriber database (testbed/open5gs) and adds
device.ipv4Address before calling the QoS provider.

Resolution is best-effort: if SUBSCRIBER_DB_URI is unset or the DB is
unreachable, None is returned and the request is sent unchanged.
"""

from __future__ import annotations

import logging

from backend.config import settings

_log = logging.getLogger(__name__)


def resolve_ue_ipv4(phone_number: str | None) -> str | None:
    if not phone_number or not settings.subscriber_db_uri:
        return None
    try:
        from pymongo import MongoClient

        with MongoClient(settings.subscriber_db_uri, serverSelectionTimeoutMS=1500) as client:
            sub = client.get_default_database().subscribers.find_one(
                {"msisdn": phone_number.lstrip("+")}, {"slice.session.ue": 1}
            )
    except Exception as exc:  # DB unreachable or pymongo missing: no enrichment
        _log.warning("UE IP resolution failed for %s: %s", phone_number, exc)
        return None

    for slice_ in (sub or {}).get("slice", []):
        for session in slice_.get("session", []):
            ipv4 = (session.get("ue") or {}).get("ipv4")
            if ipv4:
                return ipv4
    return None
