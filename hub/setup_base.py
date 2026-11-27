"""Aggiunge la Base all'ambiente locale e conserva le credenziali già create."""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from secrets import token_urlsafe

from collect_base import BASE_ID


def configure(path, url):
    if not re.fullmatch(r"http[s]?://[a-zA-Z0-9.-]+(?::[0-9]{1,5})?/api/state", url):
        raise ValueError("Usa l'URL HTTP o HTTPS della Base con percorso /api/state")
    lines = path.read_text(encoding="utf-8").splitlines()
    device_lines = [line for line in lines if line.startswith("HUB_DEVICES_JSON=")]
    if len(device_lines) != 1:
        raise ValueError("Configurazione HUB_DEVICES_JSON assente o duplicata")
    devices = json.loads(device_lines[0].split("=", 1)[1])
    device = devices.setdefault(BASE_ID, {"device_type": "base", "token": token_urlsafe(32)})
    token = device["token"]
    if device["device_type"] != "base" or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
        raise ValueError("Configurazione della Base esistente non valida")
    config = {
        "HUB_DEVICES_JSON": json.dumps(devices, separators=(",", ":")),
        "HUB_BASE_URL": url,
        "HUB_BASE_TOKEN": token,
    }
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL di /api/state della Base")
    args = parser.parse_args()
    try:
        configure(Path(__file__).resolve().with_name(".env"), args.url)
    except FileNotFoundError:
        parser.exit(1, "Esegui prima setup_demo.py.\n")
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Configurazione Base non riuscita. Controlla l'URL e il file .env.\n")
    print(f"Base configurata: {BASE_ID}.")
