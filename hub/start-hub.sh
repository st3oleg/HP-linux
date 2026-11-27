#!/usr/bin/env bash
set -euo pipefail

hub_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)

install_desktop() {
    local desktop launcher script
    desktop=$(xdg-user-dir DESKTOP)
    launcher="$desktop/Avvia Hub Terminator.desktop"
    script="$hub_dir/start-hub.sh"
    # Le virgolette in Exec gestiscono i percorsi con spazi.
    if [[ "$script" == *[\$\"\`\\%]* || "$script" == *$'\n'* ]]; then
        printf 'Percorso non compatibile con il collegamento Desktop.\n' >&2
        return 1
    fi
    mkdir -p -- "$desktop"
    if [[ -e "$launcher" || -L "$launcher" ]]; then
        printf 'Collegamento già presente: %s\n' "$launcher"
        return
    fi
    (
        set -C
        printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Avvia Hub Terminator' \
            "Exec=/bin/bash \"$script\" --desktop" 'Icon=utilities-terminal' 'Terminal=true' > "$launcher"
    )
    chmod u+x -- "$launcher"
    printf 'Collegamento creato: %s\n' "$launcher"
}

case "${1:-}" in
    --install-desktop) install_desktop; exit ;;
    --desktop)
        close_terminal() {
            local result=$?
            if (( result != 0 )); then
                printf '\nAvvio non riuscito (uscita %s).\n' "$result"
            fi
            if [[ -t 0 ]]; then
                read -r -p 'Premi Invio per chiudere… ' unused || true
            fi
        }
        trap close_terminal EXIT
        ;;
    "") ;;
    *) printf 'Uso: %s [--install-desktop]\n' "$0" >&2; exit 2 ;;
esac

cd -- "$hub_dir"
if [[ ! -s .env ]]; then
    printf 'Manca hub/.env. Configura prima l’hub e l’antenna.\n' >&2
    exit 1
fi

sudo -v
sudo systemctl start docker
sudo docker compose --env-file .env --profile base up -d --build --wait
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8090/healthz
printf '\nHub attivo: http://127.0.0.1:8090/\n'
printf '\nCollettore Base:\n'
sudo docker compose --profile base logs --tail 5 base
if command -v tailscale >/dev/null; then
    printf '\nAccesso da Windows tramite Tailscale:\n'
    tailscale serve status || true
fi
