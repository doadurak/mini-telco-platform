"""
QoS profile vocabulary — single source of truth.

CAMARA QoD leaves qosProfile names operator-defined. Two vocabularies exist:

  Operator profiles  : the profiles the southbound NEF-QoS / PCF actually
                       enforces (FRONT-research-group/NEF-QoS QOS_MAPPING).
  Semantic classes   : intent-level classes the planners emit
                       ("video streaming", "gaming", ...).

Every semantic class maps to the smallest operator profile whose maximum
bit rate covers the class's target bit rate. The executor translates a
semantic class to its operator profile immediately before the provider call,
so providers only ever receive profiles they support.
"""

from __future__ import annotations

# Operator profiles — must match NEF-QoS QOS_MAPPING (marBwDl/marBwUl, mediaType)
OPERATOR_PROFILES: dict[str, dict[str, str]] = {
    "QOS_E": {"maxBandwidth": "1 Mbps", "mediaType": "VIDEO", "description": "Basic video"},
    "QOS_S": {"maxBandwidth": "4 Mbps", "mediaType": "VIDEO", "description": "Small video"},
    "QOS_M": {"maxBandwidth": "8 Mbps", "mediaType": "VIDEO", "description": "Medium video"},
    "QOS_L": {"maxBandwidth": "20 Mbps", "mediaType": "AUDIO", "description": "Large / high-quality"},
}

# Semantic classes — target bit rate and the operator profile that covers it
SEMANTIC_PROFILES: dict[str, dict[str, str]] = {
    "QOS_CRITICAL_COMMS": {"target": "2 Mbps", "operatorProfile": "QOS_S",
                           "description": "Critical communications / public safety"},
    "QOS_E_STREAMING": {"target": "3 Mbps", "operatorProfile": "QOS_S",
                        "description": "Enhanced video streaming"},
    "QOS_LOW_LATENCY": {"target": "5 Mbps", "operatorProfile": "QOS_M",
                        "description": "Low-latency real-time traffic"},
    "QOS_GAMING": {"target": "10 Mbps", "operatorProfile": "QOS_L",
                   "description": "Cloud / online gaming"},
}

VALID_PROFILES: frozenset[str] = frozenset(OPERATOR_PROFILES) | frozenset(SEMANTIC_PROFILES)


def to_operator_profile(profile: str | None) -> str | None:
    """Return the operator profile a requested profile is enforced as (None if unknown)."""
    if profile in OPERATOR_PROFILES:
        return profile
    if profile in SEMANTIC_PROFILES:
        return SEMANTIC_PROFILES[profile]["operatorProfile"]
    return None
