from backend.capif.client import discover_services, get_invoker_id


def get_security_token(service_id: str) -> str:
    """
    Returns a CAPIF security token for the given service.
    Full OAuth2 token exchange is not yet implemented; returns a stub token
    derived from the registered invoker ID. Replace with a real token
    request to the CAPIF security API when production credentials are available.
    """
    invoker_id = get_invoker_id() or "SAMPLE_INVOKER_ID"
    return f"bearer-stub-{service_id}-{invoker_id}"


def discovery_summary() -> dict:
    return discover_services()
