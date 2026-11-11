from pathlib import Path
from typing import Any

from .infrai_client import InfraiClient


def build_messages(shipment: dict[str, Any]) -> list[dict[str, str]]:
    shipment_id = shipment["shipment_id"]
    files = shipment.get("proof_files", [])
    if not files:
        raise ValueError(f"shipment {shipment_id} has no proof files")
    return [{"shipment_id": shipment_id, "proof_file": str(name)} for name in files]


def process_shipment(shipment: dict[str, Any], client: InfraiClient, queue: str) -> list[dict[str, Any]]:
    results = []
    for message in build_messages(shipment):
        filename = Path(message["proof_file"]).name
        token = f"{message['shipment_id']}:{filename}"
        image_data = Path(message["proof_file"]).read_bytes()
        uploaded = client.upload(image_data, filename, "upload-" + token)
        image_id = str(uploaded["id"])
        resized = client.resize(image_id, "resize-" + token)
        event = {"event": "proof_processed", "shipment_id": message["shipment_id"], "image_id": image_id, "review_copy": resized.get("id", image_id)}
        client.publish(queue, event, "event-" + token)
        results.append(event)
    return results
