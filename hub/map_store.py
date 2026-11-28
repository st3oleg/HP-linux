import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

from recordings import register_recordings

from flask import Response, jsonify, request, send_file


WIDGET_KEYS = {
    "w_rover_status", "w_rover_alt", "w_rover_imu",
    "w_base_heartbeat", "w_base_coords",
}


def valid_ring(ring):
    return (
        isinstance(ring, list) and len(ring) >= 4 and ring[0] == ring[-1]
        and all(
            isinstance(point, list) and 2 <= len(point) <= 3
            and all(type(value) in (float, int) for value in point)
            and -180 <= point[0] <= 180 and -90 <= point[1] <= 90
            and (len(point) == 2 or abs(point[2]) <= 1e10)
            for point in ring
        )
    )


def valid_collection(collection):
    if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
        return False
    features = collection.get("features")
    if not isinstance(features, list):
        return False
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            return False
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            return False
        coordinates = geometry.get("coordinates")
        kind = geometry.get("type")
        if kind == "Polygon":
            coordinates = [coordinates]
        elif kind != "MultiPolygon":
            return False
        if not isinstance(coordinates, list) or not coordinates or not all(
            isinstance(polygon, list) and polygon and all(map(valid_ring, polygon))
            for polygon in coordinates
        ):
            return False
        if not isinstance(feature.get("properties"), dict):
            return False
    return True


def register_map(app, here, devices, list_devices, connect_events):
    rover_ids = sorted(device_id for device_id, device in devices.items() if device["device_type"] == "rover")
    db_path = Path(os.environ.get("HUB_MAP_DB", here / "map-data" / "perimeters.sqlite3"))

    def connect():
        return sqlite3.connect(db_path, timeout=3)

    register_recordings(app, here, devices, connect)

    @app.errorhandler(sqlite3.Error)
    def storage_unavailable(_error):
        app.logger.warning("Archivio mappa non disponibile")
        return jsonify(error="map_storage_unavailable"), 503

    @app.get("/index.html")
    def index():
        return send_file(here / "index.html")

    @app.get("/api/v1/map/available")
    def available():
        return Response("terminator-hub-map", headers={"Access-Control-Allow-Origin": "*"})

    @app.get("/scatter_analysis.html")
    def scatter_analysis():
        return send_file(here / "scatter_analysis.html")

    @app.get("/api/v1/map/scatter")
    def scatter_samples():
        window = request.args.get("window", "live")
        if window not in ("live", "history"):
            return jsonify(error="invalid_scatter_window"), 400
        if not rover_ids:
            return jsonify(rover_id=None, samples=[])
        rover_id = rover_ids[0]
        seconds = 900 if window == "history" else 45
        now = time.time()
        with connect_events() as db:
            rows = db.execute(
                """
                SELECT event->'payload'->'gnss' AS gnss
                FROM hub_events
                WHERE device_id = %s
                  AND received_at >= now() - make_interval(secs => %s)
                  AND event->>'event_type' IN ('status', 'telemetry')
                ORDER BY received_at DESC, boot_id DESC, sequence DESC
                LIMIT 3000
                """,
                (rover_id, seconds),
            ).fetchall()
        samples = {}
        for row in rows:
            gnss = row["gnss"]
            if not isinstance(gnss, dict):
                continue
            timestamp, lat, lon = (gnss.get(key) for key in ("fix_timestamp", "lat", "lon"))
            status = gnss.get("rtk_status")
            if (
                type(timestamp) not in (int, float) or not now - seconds <= timestamp <= now + 5
                or type(lat) not in (int, float) or not -90 <= lat <= 90
                or type(lon) not in (int, float) or not -180 <= lon <= 180
                or (lat, lon) == (0, 0)
                or not isinstance(status, str) or status == "NO FIX"
            ):
                continue
            samples.setdefault(timestamp, {"fix_timestamp": timestamp, "lat": lat, "lon": lon, "rtk_status": status})
        return jsonify(rover_id=rover_id, samples=[samples[key] for key in sorted(samples)])

    @app.get("/runtime-config.js")
    def map_config():
        urls = sorted(
            device["dashboard_url"] for device in devices.values()
            if device.get("device_type") == "rover" and device.get("dashboard_url")
        )
        rover_origin = ""
        if len(urls) == 1:
            url = urlsplit(urls[0])
            rover_origin = f"{url.scheme}://{url.netloc}"
        config = {"sharedMap": True, "roverOrigin": rover_origin}
        return Response(f"window.TERMINATOR_CONFIG = {json.dumps(config)};", mimetype="application/javascript")

    @app.get("/api/v1/map/state")
    def map_state():
        devices_data = list_devices().get_json()
        devices_state = devices_data["devices"]
        result = {"rover": {"lat": None, "lon": None, "online": False}, "base": None}
        for kind in ("rover", "base"):
            candidates = [device for device in devices_state if device["device_type"] == kind and device["status_event"]]
            if not candidates:
                continue
            device = min(candidates, key=lambda entry: entry["status_age_seconds"])
            online = device["status_age_seconds"] <= devices_data["stale_after_seconds"]
            event = device["status_event"]
            payload = event["payload"]
            if kind == "base":
                base = payload.get("base")
                if not isinstance(base, dict):
                    continue
                position = base.get("position")
                if isinstance(position, dict):
                    result["base"] = {
                        "lat": position.get("lat"),
                        "lon": position.get("lon"),
                        "available": online and base.get("available") is True,
                    }
            else:
                rover = payload.get("gnss")
                if not isinstance(rover, dict):
                    continue
                rtcm = payload.get("rtcm")
                result["rover"] = {
                    "lat": rover.get("lat"),
                    "lon": rover.get("lon"),
                    "rtk_status": rover.get("rtk_status"),
                    "online": online,
                    "rtcm": rtcm if isinstance(rtcm, dict) else None,
                    "last_seen": rover.get("fix_timestamp"),
                    "age_seconds": device["status_age_seconds"],
                }
        return jsonify(result)

    @app.get("/impostazioni_widgets.html")
    def widget_settings():
        return send_file(here / "impostazioni_widgets.html")

    @app.route("/api/v1/map/widgets", methods=["GET", "PATCH"])
    def widgets():
        updates = {}
        if request.method == "PATCH":
            if request.headers.get("X-Map-Action") != "save-widgets":
                return jsonify(error="invalid_action"), 403
            updates = request.get_json(silent=True)
            if (
                not isinstance(updates, dict)
                or not updates
                or not updates.keys() <= WIDGET_KEYS
                or any(type(value) is not bool for value in updates.values())
            ):
                return jsonify(error="invalid_widget_preferences"), 400

        with closing(connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS widget_preferences (name TEXT PRIMARY KEY, visible INTEGER NOT NULL)")
            if updates:
                db.executemany(
                    "INSERT INTO widget_preferences VALUES (?, ?) "
                    "ON CONFLICT(name) DO UPDATE SET visible = excluded.visible",
                    updates.items(),
                )
            rows = db.execute("SELECT name, visible FROM widget_preferences").fetchall()
            return jsonify({name: bool(visible) for name, visible in rows})

    @app.route("/api/v1/map/perimeters", methods=["GET", "PUT"])
    def perimeters():
        if request.method == "PUT":
            if request.headers.get("X-Map-Action") != "save-perimeters":
                return jsonify(error="invalid_action"), 403
            data = request.get_json(silent=True)
            if (
                not isinstance(data, dict)
                or type(data.get("revision")) is not int
                or not 0 <= data["revision"] < 2**63 - 1
                or not valid_collection(data.get("collection"))
            ):
                return jsonify(error="invalid_perimeters"), 400
            try:
                serialized = json.dumps(data["collection"], allow_nan=False)
            except (ValueError, RecursionError):
                return jsonify(error="invalid_perimeters"), 400

        with closing(connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS perimeters (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, collection TEXT NOT NULL)")
            if request.method == "GET":
                row = db.execute("SELECT revision, collection FROM perimeters WHERE id = 1").fetchone()
                if row is None:
                    return jsonify(revision=0, collection={"type": "FeatureCollection", "features": []})
                return jsonify(revision=row[0], collection=json.loads(row[1]))

            if data["revision"] == 0:
                saved = db.execute(
                    "INSERT OR IGNORE INTO perimeters VALUES (1, 1, ?)", (serialized,)
                )
            else:
                saved = db.execute(
                    "UPDATE perimeters SET revision = revision + 1, collection = ? WHERE id = 1 AND revision = ?",
                    (serialized, data["revision"]),
                )
            if saved.rowcount != 1:
                return jsonify(error="revision_conflict"), 409
            return jsonify(revision=data["revision"] + 1)
