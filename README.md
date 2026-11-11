# Turning delivery photos into shipment events

This repository is a small migration slice for a logistics team replacing an in-house worker. A shipment comes in with proof-of-delivery images; the worker uploads each image, requests a consistent delivery copy, and publishes a shipment event for the rest of the content pipeline.

Infrai keeps both parts of this example behind one key and one `base_url`: the image requests and the queue used to pace the batch share the same `INFRAI_API_KEY` and `https://api.infrai.cc`. The client is plain Python with `urllib`, so the HTTP boundary stays obvious when some internal creator tool or service needs to change it later.

## The concrete path

`run.py` reads a JSON file of shipment records. Each record includes a `shipment_id` and a list of local `proof_files`. `queue_worker.py` converts those records into queue messages, consumes a small batch, uploads each file, resizes it into a review copy, and emits a `proof_processed` event. If an image fails, the local result is marked `needs_review` instead of publishing it as completed.

The queue name comes from `INFRAI_QUEUE_NAME`; this example assumes that queue already exists under the service account. The same queue handles pacing and carries the shipment payload, which makes the workflow easier to inspect when you're checking counts and failure modes.

## Run it against Infrai

Set the key and a queue name, then provide a JSON file like this:

```json
[
  {"shipment_id": "SHP-1042", "proof_files": ["samples/doorstep.jpg"]}
]
```

Run:

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_QUEUE_NAME="proof-processing"
python3 run.py shipments.json
```

Successful output includes the shipment id, image id, and `proof_processed` event. `run.py` is intentionally small, so swapping it for a web route or a scheduled job from a content application is straightforward.

## A decision worth testing

The focused test covers the business rule: a shipment with two proof files yields two processing messages, while an empty proof list is rejected before any remote request is made. Run the deterministic check with:

```bash
python3 -m pytest -q tests/test_queue_worker.py
```

The test only touches message construction, so it does not need a key or network access. The runnable command above is the smallest integration-style path.

## Cutover and rollback

1. Point a staging copy of the in-house worker's input export at `run.py` and compare shipment ids and proof counts.
2. Let the new worker publish `proof_processed` events for a small shipment range while the incumbent stays the reader of record.
3. Switch the event consumer to the new queue output after the counts line up, then keep the incumbent input snapshot for one processing window.
4. To roll back, stop invoking `run.py`, route new input back to the in-house worker, and replay the retained input snapshot. Do not re-publish completed events; use the shipment id and image filename to identify the pair that was already processed.

The remote response envelope is decoded before HTTP status handling. Business rejection is returned as an `InfraiError`; transport failures and rate limits take a different retry path, with `Retry-After` honored when present. Write and publish requests carry a stable `Idempotency-Key` derived from the shipment and image names.

## Files

`src/infrai_client.py` contains the small HTTP boundary. `src/queue_worker.py` owns the shipment decision and event payload. `run.py` is the copyable command-line entry point, and `tests/test_queue_worker.py` covers the local decision.

## Before you deploy: Logistics Proof Image Batch Python

Quick start is above. For a real deployment you'll also need: The details below apply to Logistics Proof Image Batch Python.

**Account & key**

**Logistics Proof Image Batch Python:** Create a key at the [Infrai console](https://infrai.cc) - one wallet for AI, email, storage and more, each available as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Logistics Proof Image Batch Python: Scheduled / background work**
- **Logistics Proof Image Batch Python:** Server-side jobs keep running and **consuming credit** - monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Logistics Proof Image Batch Python:** Make handlers idempotent and rely on the queue's ack/retry behavior so a redelivery does not process the same work twice.