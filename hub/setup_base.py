"""Aggiunge la Base all'ambiente locale e conserva le credenziali già create."""

import argparse
import re
from pathlib import Path

from collect_base import BASE_ID
from device_config import load_config, register, save_config


def configure(path, url, *, remove_demo=False):
    if not re.fullmatch(r"http[s]?://[a-zA-Z0-9.-]+(?::[0-9]{1,5})?/api/state", url):
        raise ValueError("Usa l'URL HTTP o HTTPS della Base con percorso /api/state")
    lines, devices = load_config(path)
    token = register(devices, BASE_ID, "base")
    if remove_demo:
        for device_id in ("demo-base", "demo-rover"):
            devices.pop(device_id, None)
    save_config(path, lines, devices, HUB_BASE_URL=url, HUB_BASE_TOKEN=token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove-demo", action="store_true", help="Disattiva le identità della demo")
    parser.add_argument("url", help="URL di /api/state della Base")
    args = parser.parse_args()
    try:
        configure(Path(__file__).resolve().with_name(".env"), args.url, remove_demo=args.remove_demo)
    except FileNotFoundError:
        parser.exit(1, "Esegui prima setup_demo.py.\n")
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Configurazione Base non riuscita. Controlla l'URL e il file .env.\n")
    print(f"Base configurata: {BASE_ID}.")
    if args.remove_demo:
        print("Identità demo disattivate. Gli eventi già salvati restano nel database.")
