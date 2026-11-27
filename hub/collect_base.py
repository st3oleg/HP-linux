"""Legge lo stato della Base e lo invia all'hub, una volta ogni 10 secondi."""

import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from uuid import uuid4


BASE_ID = "base-rtk-01"
HUB_URL = "http://web:8080/api/v1/events"
POLL_SECONDS = 10
MAX_RESPONSE_BYTES = 65536


def measure_time(timestamp):
    if type(timestamp) not in (int, float):
        return None
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def coordinate(value, limit):
    return value if type(value) in (int, float) and -limit <= value <= limit else None


def base_event(state, boot_id, sequence, uptime_ms):
    base = state.get("base") if isinstance(state, dict) else None
    if not isinstance(base, dict) or type(base.get("available")) is not bool:
        raise ValueError("Stato Base assente")
    available = base["available"]
    lat = coordinate(base.get("lat"), 90) if available else None
    lon = coordinate(base.get("lon"), 180) if available else None
    position = {"lat": lat, "lon": lon} if lat is not None and lon is not None else None
    quality = base.get("quality")
    source = base.get("source")
    age = base.get("age_seconds")
    return {
        "schema_version": 1,
        "device_id": BASE_ID,
        "device_type": "base",
        "boot_id": boot_id,
        "sequence": sequence,
        "event_type": "status",
        "observed_at": measure_time(base.get("updated_at")),
        "monotonic_ms": uptime_ms,
        "payload": {
            "base": {
                "available": available,
                "position": position,
                "quality": quality if type(quality) is int and 0 <= quality <= 9 else None,
                "source": source[:120] if isinstance(source, str) else None,
                "age_seconds": age if type(age) in (int, float) and 0 <= age < math.inf else None,
            }
        },
    }


def read_base(url):
    with urlopen(url, timeout=5) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("Risposta Base troppo grande")
    return json.loads(data)


def send_event(event, token):
    request = Request(
        HUB_URL,
        data=json.dumps(event, allow_nan=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urlopen(request, timeout=5) as response:
        if response.status not in (200, 201):
            raise ValueError("Risposta hub inattesa")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    url = os.environ["HUB_BASE_URL"]
    token = os.environ["HUB_BASE_TOKEN"]
    if not url or not token:
        raise SystemExit("Esegui prima setup_base.py")
    boot_id = str(uuid4())
    started = time.monotonic()
    sequence = 0
    previous = None
    while True:
        try:
            state = read_base(url)
            event = base_event(state, boot_id, sequence, int((time.monotonic() - started) * 1000))
            sequence += 1
        except (OSError, ValueError, RecursionError) as error:
            outcome = f"Lettura Base fallita ({getattr(error, 'code', type(error).__name__)})"
        else:
            try:
                send_event(event, token)
            except (OSError, ValueError) as error:
                outcome = f"Invio all'hub fallito ({getattr(error, 'code', type(error).__name__)})"
            else:
                outcome = "Stato Base salvato nell'hub"
        if outcome != previous:
            logging.info(outcome)
            previous = outcome
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
