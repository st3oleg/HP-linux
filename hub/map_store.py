import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

from flask import Response, jsonify, request, send_file


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


def register_map(app, here, devices, list_devices):
    db_path = Path(os.environ.get("HUB_MAP_DB", here / "map-data" / "perimeters.sqlite3"))

    def connect():
        return sqlite3.connect(db_path, timeout=3)

    @app.errorhandler(sqlite3.Error)
    def storage_unavailable(_error):
        app.logger.warning("Archivio perimetri non disponibile")
        return jsonify(error="map_storage_unavailable"), 503

    @app.get("/index.html")
    def index():
        return send_file(here / "index.html")

    @app.get("/api/v1/map/available")
    def available():
        return Response("terminator-hub-map", headers={"Access-Control-Allow-Origin": "*"})

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
