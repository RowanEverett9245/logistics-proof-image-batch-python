import json
import sys

from src.infrai_client import InfraiClient
from src.queue_worker import process_shipment


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 run.py shipments.json")
    with open(sys.argv[1], encoding="utf-8") as stream:
        shipments = json.load(stream)
    client = InfraiClient()
    queue = __import__("os").environ["INFRAI_QUEUE_NAME"]
    consumed = client.consume(queue)
    print(json.dumps({"consumed": consumed}, indent=2))
    for shipment in shipments:
        print(json.dumps(process_shipment(shipment, client, queue), indent=2))


if __name__ == "__main__":
    main()
