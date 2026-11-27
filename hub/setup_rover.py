"""Registra un Rover e, se richiesto, crea il suo file credenziali locale."""

import argparse
import os
import re
from pathlib import Path

from device_config import load_config, register, save_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device_id")
    parser.add_argument("hub_url", help="URL HTTPS completo di /api/v1/events")
    parser.add_argument("--output", type=Path, help="Nuovo file credenziali per il Rover")
    args = parser.parse_args()
    if not re.fullmatch(r"https://[a-zA-Z0-9.-]+(?::[0-9]{1,5})?/api/v1/events", args.hub_url):
        parser.error("Usa un URL HTTPS che termini con /api/v1/events")
    path = Path(__file__).resolve().with_name(".env")
    try:
        lines, devices = load_config(path)
        token = register(devices, args.device_id, "rover")
        if args.output is not None and args.output.exists():
            parser.error("Il file di destinazione esiste già")
        save_config(path, lines, devices)
        if args.output is not None:
            fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write(f"ROVER_HUB_URL={args.hub_url}\n")
                output.write(f"ROVER_HUB_DEVICE_ID={args.device_id}\n")
                output.write(f"ROVER_HUB_TOKEN={token}\n")
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Registrazione Rover non riuscita. Controlla i percorsi e il catalogo locale.\n")
    print(f"Rover configurato: {args.device_id}.")


if __name__ == "__main__":
    main()
