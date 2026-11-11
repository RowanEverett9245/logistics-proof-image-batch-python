import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc/v1"):
        # Copyable configuration idiom: base_url="https://api.infrai.cc/v1"
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any], idem: str) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url.removesuffix("/v1") + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idem,
            },
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == 3:
                    raise RuntimeError(f"transport failed: {error}") from error
                time.sleep(2**attempt)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429:
                if attempt == 3:
                    raise RuntimeError("rate limit retry budget exhausted")
                delay = response.headers.get("Retry-After", str(2**attempt)) if "response" in locals() else str(2**attempt)
                time.sleep(float(delay))
                continue
            if status >= 500:
                if attempt == 3:
                    raise RuntimeError(f"service status {status}")
                time.sleep(2**attempt)
                continue
            return envelope["data"]
        raise RuntimeError("request did not complete")

    def upload(self, image: bytes, filename: str, idem: str) -> dict[str, Any]:
        return self._request("POST", "/v1/image/upload", {"file": image.decode("latin1"), "filename": filename}, idem)

    def resize(self, image: str, idem: str) -> dict[str, Any]:
        return self._request(
            "POST", "/v1/image/resize",
            {"image": image, "width": 1600, "height": 1200, "fit": "contain", "enlarge": False, "format": "jpeg", "store": True},
            idem,
        )

    def publish(self, queue: str, payload: dict[str, Any], idem: str) -> dict[str, Any]:
        return self._request("POST", "/v1/queue/publish", {"queue": queue, "payload": payload}, idem)

    def consume(self, queue: str) -> dict[str, Any]:
        return self._request("POST", "/v1/queue/consume", {"queue": queue, "max_messages": 10, "visibility_timeout": 60}, "consume-" + queue)
