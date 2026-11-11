import pytest

from src.queue_worker import build_messages


def test_two_proof_files_become_two_shipment_messages():
    shipment = {"shipment_id": "SHP-1042", "proof_files": ["front.jpg", "signature.jpg"]}
    assert build_messages(shipment) == [
        {"shipment_id": "SHP-1042", "proof_file": "front.jpg"},
        {"shipment_id": "SHP-1042", "proof_file": "signature.jpg"},
    ]


def test_empty_proof_list_is_rejected_before_remote_work():
    with pytest.raises(ValueError, match="no proof files"):
        build_messages({"shipment_id": "SHP-1043", "proof_files": []})
