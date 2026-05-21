from backend.models import CatalogOperation, CatalogService


CATALOG: dict[str, CatalogService] = {
    "qod": CatalogService(
        service_id="qod",
        title="Quality-On-Demand",
        version="v1",
        description="Temporary QoS session creation based on CAMARA QoD semantics.",
        base_path="/quality-on-demand/v1",
        source="CAMARA qod_v1.1.0.yaml and FRONT-research-group/camara-QoD",
        operations=[
            CatalogOperation(
                operation_id="createSession",
                method="POST",
                path="/sessions",
                summary="Create a temporary QoD session",
            )
        ],
    ),
    "qos-profiles": CatalogService(
        service_id="qos-profiles",
        title="QoS Profiles",
        version="v1",
        description="Discover available QoS profiles for a target device.",
        base_path="/qos-profiles/v1",
        source="CAMARA qos_profiles_v1.1.0.yaml and FRONT-research-group/camara-QoD",
        operations=[
            CatalogOperation(
                operation_id="retrieveQoSProfiles",
                method="POST",
                path="/retrieve-qos-profiles",
                summary="Retrieve all applicable QoS profiles",
            ),
            CatalogOperation(
                operation_id="getQosProfile",
                method="GET",
                path="/qos-profiles/{name}",
                summary="Retrieve a specific QoS profile",
            ),
        ],
    ),
    "qos-provisioning": CatalogService(
        service_id="qos-provisioning",
        title="QoS Provisioning",
        version="v1",
        description="Create longer-lived QoS assignments for a target device via NEF AsSessionWithQoS.",
        base_path="/qos-provisioning/v1",
        source="CAMARA qos_provisioning_v1.1.0.yaml and FRONT-research-group/NEF-QoS",
        operations=[
            CatalogOperation(
                operation_id="createQosAssignment",
                method="POST",
                path="/qos-assignments",
                summary="Create a QoS assignment",
            )
        ],
    ),
    "location-retrieval": CatalogService(
        service_id="location-retrieval",
        title="Device Location Retrieval",
        version="0.5",
        description="Retrieve last known device location through CAMARA to NEF translation.",
        base_path="/location-retrieval/v0.5",
        source="FRONT-research-group/CamaraLocationRetrieval",
        operations=[
            CatalogOperation(
                operation_id="retrieveLocation",
                method="POST",
                path="/retrieve",
                summary="Retrieve last known device location",
            )
        ],
    ),
}
