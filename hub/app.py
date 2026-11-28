import hmac
import json
import os
import re
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from urllib.parse import urlsplit
from pathlib import Path

import psycopg
from flask import Flask, jsonify, request, send_file
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from werkzeug.exceptions import BadRequest

from map_store import register_map


HERE = Path(__file__).resolve().parent
MAX_BIGINT = 2**63 - 1


def strict_json(value):
    def reject_constant(constant):
        raise ValueError(f"Numero JSON non valido: {constant}")

    return json.loads(value, parse_constant=reject_constant)


def canonical_json(value):
    return json.dumps(value, allow_nan=False, ensure_ascii=False)


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 65536
    schema_path = HERE / "schema.json"
    if not schema_path.exists():
        schema_path = HERE.parent / "schemas" / "hub-event-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    devices = json.loads(os.environ["HUB_DEVICES_JSON"])
    stale_after = int(os.environ.get("HUB_STALE_AFTER_SECONDS", "30"))
    if not isinstance(devices, dict) or not devices or stale_after < 1:
        raise ValueError("Configurazione hub non valida")
    tokens = set()
    for device_id, device in devices.items():
        token = device["token"]
        if (
            not re.fullmatch(schema["properties"]["device_id"]["pattern"], device_id)
            or not re.fullmatch(
                schema["properties"]["device_type"]["pattern"], device["device_type"]
            )
            or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token)
            or token in tokens
        ):
            raise ValueError("Identità o token del dispositivo non valido")
        tokens.add(token)

    def connect():
        return psycopg.connect(connect_timeout=3, row_factory=dict_row)

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.errorhandler(413)
    def body_too_large(_error):
        return jsonify(error="payload_too_large"), 413

    @app.errorhandler(psycopg.Error)
    def database_error(_error):
        app.logger.warning("Operazione PostgreSQL fallita")
        return jsonify(error="database_unavailable"), 503

    @app.errorhandler(psycopg.DataError)
    def database_rejected_data(_error):
        return jsonify(error="invalid_event_data"), 400

    @app.get("/")
    def dashboard():
        return send_file(HERE / "dashboard.html")

    @app.get("/dashboard-background.png")
    def dashboard_background():
        return send_file(HERE / "dashboard-background.png", mimetype="image/png")

    @app.get("/healthz")
    def health():
        with connect() as conn:
            conn.execute("SELECT 1 FROM hub_events LIMIT 1")
        return jsonify(status="ok")

    @app.get("/api/v1/devices")
    def list_devices():
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT ids.device_id, latest.received_at, latest.event,
                       sample.event AS status_event, sample.received_at AS status_received_at
                FROM unnest(%s::text[]) AS ids(device_id)
                JOIN LATERAL (
                    SELECT received_at, event FROM hub_events
                    WHERE device_id = ids.device_id
                    ORDER BY received_at DESC, boot_id DESC, sequence DESC
                    LIMIT 1
                ) AS latest ON true
                LEFT JOIN LATERAL (
                    SELECT event, received_at FROM hub_events
                    WHERE device_id = ids.device_id
                      AND event->>'event_type' IN ('status', 'telemetry')
                    ORDER BY received_at DESC, boot_id DESC, sequence DESC
                    LIMIT 1
                ) AS sample ON true
                """,
                (list(devices),),
            ).fetchall()
        latest = {row["device_id"]: row for row in rows}
        now = datetime.now(timezone.utc)
        results = []
        for device_id, device in sorted(devices.items()):
            row = latest.get(device_id)
            age = max(0, (now - row["received_at"]).total_seconds()) if row else None
            results.append(
                {
                    "device_id": device_id,
                    "device_type": device["device_type"],
                    "online": age is not None and age <= stale_after,
                    "age_seconds": round(age, 1) if age is not None else None,
                    "received_at": row["received_at"].isoformat() if row else None,
                    "event": row["event"] if row else None,
                    "status_event": row["status_event"] if row else None,
                    "status_age_seconds": max(0, (now - row["status_received_at"]).total_seconds())
                    if row and row["status_received_at"] else None,
                    "dashboard_url": device.get("dashboard_url") if device["device_type"] == "rover" else None,
                }
            )
        return jsonify(
            hub={"name": os.environ.get("HUB_DISPLAY_NAME", "HP Ubuntu"), "online": True},
            devices=results,
            stale_after_seconds=stale_after,
        )

    register_map(app, HERE, devices, list_devices)

    @app.post("/api/v1/devices/<device_id>/open")
    def open_rover(device_id):
        # A cross-origin form or navigation must not trigger a Rover startup.
        if request.headers.get("X-Hub-Action") != "open-rover":
            return jsonify(error="invalid_action"), 403

        device = devices.get(device_id, {})
        page = device.get("dashboard_url")
        if device.get("device_type") != "rover" or not isinstance(page, str):
            return jsonify(error="page_unconfigured"), 404
        if not re.fullmatch(r"https?://[a-zA-Z0-9.-]+(?::[0-9]{1,5})?/autopilota\.html", page):
            return jsonify(error="page_unconfigured"), 404
        target = urlsplit(page)
        try:
            port = target.port
        except ValueError:
            return jsonify(error="page_unconfigured"), 404
        if port == 0:
            return jsonify(error="page_unconfigured"), 404

        connection_class = HTTPSConnection if target.scheme == "https" else HTTPConnection
        connection = connection_class(target.hostname, port, timeout=4)
        try:
            try:
                connection.connect()
            except ConnectionRefusedError:
                return jsonify(error="socket_unavailable"), 503
            except OSError:
                return jsonify(error="rover_unreachable"), 503

            # systemd starts the service on the incoming connection. Wait for HTTP readiness.
            connection.sock.settimeout(25)
            connection.request("HEAD", target.path)
            with connection.getresponse() as response:
                if response.status == 200:
                    return jsonify(status="ready")
                return jsonify(error="page_unavailable"), 502
        except (OSError, HTTPException):
            return jsonify(error="rover_start_failed"), 504
        finally:
            connection.close()

    @app.post("/api/v1/events")
    def receive_event():
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
            return jsonify(error="unauthorized"), 401
        device_id = next(
            (key for key, device in devices.items() if hmac.compare_digest(token, device["token"])),
            None,
        )
        if device_id is None:
            return jsonify(error="unauthorized"), 401
        if request.mimetype != "application/json":
            return jsonify(error="expected_json"), 415
        try:
            event = strict_json(request.get_data())
            validator.validate(event)
            if any(event[key] > MAX_BIGINT for key in ("sequence", "monotonic_ms")):
                return jsonify(error="integer_out_of_range"), 400
            for key in ("sequence", "monotonic_ms"):
                event[key] = int(event[key])
            canonical_json(event).encode("utf-8")
        except ValidationError:
            return jsonify(error="invalid_event"), 400
        except (BadRequest, ValueError, RecursionError):
            return jsonify(error="invalid_json"), 400
        if event["device_id"] != device_id or event["device_type"] != devices[device_id]["device_type"]:
            return jsonify(error="device_mismatch"), 403
        key = (device_id, event["boot_id"], event["sequence"])
        json_event = Jsonb(event, dumps=canonical_json)
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO hub_events (device_id, boot_id, sequence, event)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING RETURNING received_at
                """,
                (*key, json_event),
            ).fetchone()
            created = row is not None
            if not created:
                row = conn.execute(
                    """
                    SELECT received_at, event = %s AS same_event FROM hub_events
                    WHERE device_id = %s AND boot_id = %s AND sequence = %s
                    """,
                    (json_event, *key),
                ).fetchone()
                if not row["same_event"]:
                    return jsonify(error="sequence_conflict"), 409
        return jsonify(
            status="stored" if created else "duplicate",
            received_at=row["received_at"].isoformat(),
        ), 201 if created else 200

    return app
