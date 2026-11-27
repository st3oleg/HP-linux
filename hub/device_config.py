"""Gestisce il catalogo locale dei dispositivi nel file .env dell'hub."""

import json
import os
import re
import tempfile
from pathlib import Path
from secrets import token_urlsafe


def load_config(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    device_lines = [line for line in lines if line.startswith("HUB_DEVICES_JSON=")]
    if len(device_lines) != 1:
        raise ValueError("Configurazione HUB_DEVICES_JSON assente o duplicata")
    devices = json.loads(device_lines[0].split("=", 1)[1])
    if not isinstance(devices, dict):
        raise ValueError("Catalogo non valido")
    return lines, devices


def register(devices, device_id, kind):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", device_id):
        raise ValueError("Identità non valida")
    if device_id in ("demo-base", "demo-rover"):
        raise ValueError("Identità riservata alla demo")
    device = devices.setdefault(device_id, {"device_type": kind, "token": token_urlsafe(32)})
    token = device["token"]
    if device["device_type"] != kind or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
        raise ValueError("Identità esistente incompatibile")
    return token


def save_config(path, lines, devices, **extra):
    config = {"HUB_DEVICES_JSON": json.dumps(devices, separators=(",", ":")), **extra}
    updated = [line for line in lines if line.split("=", 1)[0] not in config]
    updated.extend(f"{key}={value}" for key, value in config.items())
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".env.", delete=False
    ) as env:
        temp = Path(env.name)
        try:
            env.write("\n".join(updated) + "\n")
            env.close()
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
