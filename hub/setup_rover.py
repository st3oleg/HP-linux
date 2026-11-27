"""Registra un Rover e, se richiesto, crea il suo file credenziali locale."""

import argparse
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from device_config import load_config, register, save_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device_id")
    parser.add_argument("hub_url", help="URL HTTPS completo di /api/v1/events")
    parser.add_argument("--output", type=Path, help="Nuovo file credenziali per il Rover")
    links = parser.add_mutually_exclusive_group()
    links.add_argument("--dashboard-url", help="URL diretto della pagina /autopilota.html del Rover")
    links.add_argument("--clear-dashboard-url", action="store_true", help="Rimuove il collegamento")
    args = parser.parse_args()
    if not re.fullmatch(r"https://[a-zA-Z0-9.-]+(?::[0-9]{1,5})?/api/v1/events", args.hub_url):
        parser.error("Usa un URL HTTPS che termini con /api/v1/events")
    if args.dashboard_url:
        page = args.dashboard_url
        if not re.fullmatch(r"https?://[a-zA-Z0-9.-]+(?::[0-9]{1,5})?/autopilota\.html", page):
            parser.error("La pagina Rover deve usare HTTP o HTTPS e terminare con /autopilota.html")
        try:
            if urlsplit(page).port == 0:
                raise ValueError
        except ValueError:
            parser.error("Porta della pagina Rover non valida")
    path = Path(__file__).resolve().with_name(".env")
    try:
        lines, devices = load_config(path)
        token = register(devices, args.device_id, "rover")
        if args.dashboard_url:
            devices[args.device_id]["dashboard_url"] = args.dashboard_url
        elif args.clear_dashboard_url:
            devices[args.device_id].pop("dashboard_url", None)
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
