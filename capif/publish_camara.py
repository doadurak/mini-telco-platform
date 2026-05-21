from backend.capif.client import publish_service

SERVICES_TO_PUBLISH = [
    {
        "name": "Quality on Demand",
        "description": "Dynamic QoS session management",
        "version": "1.1.0",
    },
    {
        "name": "QoS Profiles",
        "description": "List and retrieve technical QoS profiles",
        "version": "1.1.0",
    },
    {
        "name": "QoS Provisioning",
        "description": "Static and long-term QoS rules",
        "version": "1.1.0",
    },
]


if __name__ == "__main__":
    for service in SERVICES_TO_PUBLISH:
        print(publish_service(service))
