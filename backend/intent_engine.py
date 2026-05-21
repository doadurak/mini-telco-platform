import re

from backend.models import ExecutionStep
from backend.service_catalog import CATALOG


PHONE_PATTERN = re.compile(r"\+\d{8,15}")
DURATION_PATTERN = re.compile(
    r"(\d+)\s*(saniye|sn|second|seconds|sec|dakika|dk|minute|minutes|min|saat|hour|hours)",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"(\d+)")

QOS_HINTS = {
    # Streaming / video
    "video": "QOS_E_STREAMING",
    "stream": "QOS_E_STREAMING",
    "streaming": "QOS_E_STREAMING",
    "broadcast": "QOS_E_STREAMING",
    "live": "QOS_E_STREAMING",
    "conference": "QOS_E_STREAMING",
    "yayin": "QOS_E_STREAMING",
    # Gaming
    "game": "QOS_GAMING",
    "gaming": "QOS_GAMING",
    "oyun": "QOS_GAMING",
    # Low latency
    "latency": "QOS_LOW_LATENCY",
    "low-latency": "QOS_LOW_LATENCY",
    "gecikme": "QOS_LOW_LATENCY",
    # Critical / emergency
    "critical": "QOS_CRITICAL_COMMS",
    "emergency": "QOS_CRITICAL_COMMS",
    "mission-critical": "QOS_CRITICAL_COMMS",
    "kritik": "QOS_CRITICAL_COMMS",
}

# Keywords that signal location-retrieval
_LOCATION_KEYWORDS = (
    "location", "locate", "locating", "where", "position", "geographic",
    "coordinates", "find", "track", "gps",
    "konum", "nerede",
)

# Keywords that signal qos-provisioning (permanent/persistent assignment).
# Checked BEFORE profile detection to avoid "profile" in provisioning intents
# from triggering qos-profiles routing.
_PROVISIONING_KEYWORDS = (
    # English
    "permanent", "permanently", "persist", "persistent", "persistently",
    "indefinite", "indefinitely", "continuous", "continuously",
    "no time limit", "no expiry",
    "provision", "provisioning", "provisioned",
    "long-term", "long term",
    # Turkish
    "kalici", "kalıcı", "surekli", "sürekli",
    "daimi",       # means perpetual
    "atan", "ata", # means assign (imperative)
)

# Words that together with "profile/profil" signal profile-discovery intent.
# "profile" alone is NOT enough — it also appears in QoD/provisioning intents.
_PROFILE_DISCOVERY_WORDS = (
    # English
    "list", "available", "discover", "query", "what", "which", "supported",
    "show", "check",
    # Turkish
    "listele",       # list
    "mevcut",        # available
    "hangi",         # which
    "göster",        # show
    "sorgula",       # query
    "desteklenen",   # supported
    "uygun",         # suitable / appropriate
)


def _extract_phone_number(intent: str) -> str | None:
    match = PHONE_PATTERN.search(intent)
    return match.group(0) if match else None


def _extract_duration_seconds(intent: str) -> int:
    lowered = intent.lower()
    duration_match = DURATION_PATTERN.search(lowered)
    if duration_match:
        value = int(duration_match.group(1))
        unit = duration_match.group(2).lower()
        if unit in {"saat", "hour", "hours"}:
            return value * 3600
        if unit in {"saniye", "sn", "second", "seconds", "sec"}:
            return value  # already in seconds
        return value * 60  # minutes → seconds

    numbers = [int(m.group(1)) for m in NUMBER_PATTERN.finditer(lowered)]
    for value in numbers:
        if value < 1000:
            return value * 60
    return 15 * 60


def _select_qos_profile(intent: str) -> str:
    lowered = intent.lower()
    for hint, profile in QOS_HINTS.items():
        if hint in lowered:
            return profile
    return "QOS_E"


def _is_location_intent(lowered: str) -> bool:
    return any(kw in lowered for kw in _LOCATION_KEYWORDS)


def _is_provisioning_intent(lowered: str) -> bool:
    return any(kw in lowered for kw in _PROVISIONING_KEYWORDS)


def _is_profile_discovery_intent(lowered: str) -> bool:
    """
    Requires both a profile noun AND a discovery verb/adjective.
    This prevents intents like "apply QoS profile for 30 min" from routing
    to qos-profiles when they should route to qod.
    """
    has_profile_noun = "profile" in lowered or "profil" in lowered
    has_discovery_word = any(w in lowered for w in _PROFILE_DISCOVERY_WORDS)
    # Also catch explicit multi-word phrases
    explicit_phrases = ("hangi qos", "uygun qos")
    has_explicit = any(p in lowered for p in explicit_phrases)
    return (has_profile_noun and has_discovery_word) or has_explicit


def build_execution_plan(intent: str) -> tuple[str, list[ExecutionStep]]:
    """
    Routing order (most-specific first):
      1. Location retrieval — explicit location/position keywords
      2. QoS provisioning  — permanent/persistent assignment keywords
      3. QoS profiles      — discovery/listing intent (profile noun + discovery verb)
      4. QoD session       — default (temporary quality boost)
    """
    lowered = intent.lower()
    phone_number = _extract_phone_number(intent) or "+34600000000"

    if _is_location_intent(lowered):
        service = CATALOG["location-retrieval"]
        return (
            "deterministic",
            [
                ExecutionStep(
                    service_id=service.service_id,
                    operation_id="retrieveLocation",
                    method="POST",
                    path="/retrieve",
                    payload={
                        "device": {"phoneNumber": phone_number},
                        "maxAge": 300,
                    },
                    rationale="Intent asks for device location retrieval.",
                )
            ],
        )

    if _is_provisioning_intent(lowered):
        service = CATALOG["qos-provisioning"]
        return (
            "deterministic",
            [
                ExecutionStep(
                    service_id=service.service_id,
                    operation_id="createQosAssignment",
                    method="POST",
                    path="/qos-assignments",
                    payload={
                        "device": {"phoneNumber": phone_number},
                        "qosProfile": _select_qos_profile(intent),
                    },
                    rationale="Intent asks for long-lived QoS profile assignment.",
                )
            ],
        )

    if _is_profile_discovery_intent(lowered):
        service = CATALOG["qos-profiles"]
        return (
            "deterministic",
            [
                ExecutionStep(
                    service_id=service.service_id,
                    operation_id="retrieveQoSProfiles",
                    method="POST",
                    path="/retrieve-qos-profiles",
                    payload={"device": {"phoneNumber": phone_number}},
                    rationale="Intent asks for discovering available QoS profiles.",
                )
            ],
        )

    service = CATALOG["qod"]
    return (
        "deterministic",
        [
            ExecutionStep(
                service_id=service.service_id,
                operation_id="createSession",
                method="POST",
                path="/sessions",
                payload={
                    "device": {"phoneNumber": phone_number},
                    "qosProfile": _select_qos_profile(intent),
                    "duration": _extract_duration_seconds(intent),
                    "applicationServer": {
                        "ipv4Address": "198.51.100.10",
                        "port": 443,
                    },
                },
                rationale="Intent asks for temporary QoD session creation.",
            )
        ],
    )
