import json
from contextlib import closing
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from urllib.parse import urlencode, urlsplit

from flask import Response, jsonify, request, send_file


MAX_MISSION_BYTES = 5_000_000


def valid_filename(name):
    return (
        isinstance(name, str) and len(name) <= 255 and name.endswith(".json")
        and not any(char in name for char in "/\\")
        and all(ord(char) >= 32 and ord(char) != 127 for char in name)
    )


def read_rover(origin, path, limit):
    target = urlsplit(origin)
    cls = HTTPSConnection if target.scheme == "https" else HTTPConnection
    with closing(cls(target.hostname, target.port, timeout=8)) as conn:
        conn.request("GET", path, headers={"Accept": "application/json"})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Risposta Rover troppo grande")
    return json.loads(data)


def register_recordings(app, here, devices, connect):
    sources = {
        device_id: device["dashboard_url"]
        for device_id, device in devices.items()
        if device["device_type"] == "rover" and device.get("dashboard_url")
    }

    def ensure_archive(db):
        db.execute(
            "CREATE TABLE IF NOT EXISTS recordings ("
            "device_id TEXT NOT NULL, filename TEXT NOT NULL, title TEXT NOT NULL, "
            "points INTEGER NOT NULL, mission TEXT NOT NULL, "
            "PRIMARY KEY (device_id, filename))"
        )

    @app.get("/registrazioni.html")
    def vineyard():
        return send_file(here / "registrazioni.html")

    @app.get("/vineyard.js")
    def vineyard_js():
        return send_file(here / "vineyard.js")

    @app.get("/missioni.html")
    def recordings_page():
        return send_file(here / "missioni.html")

    @app.get("/api/v1/recordings")
    def list_recordings():
        with closing(connect()) as db:
            ensure_archive(db)
            rows = db.execute(
                "SELECT device_id, filename, title, points FROM recordings ORDER BY filename COLLATE NOCASE"
            ).fetchall()
        return jsonify(
            sources=sorted(sources),
            recordings=[
                {"device_id": device_id, "filename": filename, "title": title, "points": points}
                for device_id, filename, title, points in rows
            ],
        )

    @app.get("/api/v1/recordings/<device_id>/source")
    def list_source(device_id):
        if device_id not in sources:
            return jsonify(error="unknown_rover"), 404
        try:
            catalog = read_rover(sources[device_id], "/api/replay/missions", 1_000_000)
            if not isinstance(catalog, dict) or not isinstance(catalog.get("missions"), list):
                raise ValueError("Catalogo Rover non valido")
        except (OSError, HTTPException, ValueError, RecursionError):
            return jsonify(error="rover_unavailable"), 502
        return jsonify(missions=[name for name in catalog["missions"] if valid_filename(name)])

    @app.route("/api/v1/recordings/<device_id>/mission", methods=["GET", "POST"])
    def recording(device_id):
        filename = request.args.get("filename")
        if not valid_filename(filename):
            return jsonify(error="invalid_filename"), 400
        if request.method == "GET":
            with closing(connect()) as db:
                ensure_archive(db)
                row = db.execute(
                    "SELECT mission FROM recordings WHERE device_id = ? AND filename = ?",
                    (device_id, filename),
                ).fetchone()
            if row is None:
                return jsonify(error="mission_not_archived"), 404
            return Response(row[0], mimetype="application/json")
        if request.headers.get("X-Map-Action") != "archive-mission":
            return jsonify(error="invalid_action"), 403
        if device_id not in sources:
            return jsonify(error="unknown_rover"), 404
        try:
            query = urlencode({"filename": filename})
            mission = read_rover(sources[device_id], "/api/recordings/mission?" + query, MAX_MISSION_BYTES)
            if not isinstance(mission, dict) or not isinstance(mission.get("points"), list):
                raise ValueError("Missione Rover non valida")
            serialized = json.dumps(mission, ensure_ascii=False, allow_nan=False)
        except (OSError, HTTPException, ValueError, RecursionError):
            return jsonify(error="mission_unavailable"), 502
        title = mission.get("mission")
        with closing(connect()) as db, db:
            ensure_archive(db)
            db.execute(
                "INSERT OR IGNORE INTO recordings VALUES (?, ?, ?, ?, ?)",
                (device_id, filename, title if isinstance(title, str) else filename,
                 len(mission["points"]), serialized),
            )
        return jsonify(status="archived")
