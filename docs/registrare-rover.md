# Registrare un Rover nell'hub

La registrazione crea un'identità e un token dedicati. Si può fare con il Rover spento. Dopo l'applicazione della configurazione, la dashboard mostra il Rover in attesa fino al primo evento.

Dalla cartella `hub` sull'HP, sostituisci `NOME-HP` con il nome HTTPS restituito da Tailscale Serve. Il file di configurazione per il Rover viene creato con permessi `600` sotto la cartella personale.

```bash
mkdir -p "$HOME/.config/terminator"
python3 setup_rover.py rover-01 https://NOME-HP.ts.net/api/v1/events --output "$HOME/.config/terminator/rover-01.env"
sudo docker compose --profile base up -d --wait --no-deps web
```

Il programma riusa l'identità se è già configurata come Rover. Lascia intatti gli altri dispositivi. Trasferisci il file di credenziali direttamente al Rover tramite un canale privato e caricalo nell'ambiente del servizio Rover. Il file contiene il token e va tenuto fuori dal repository.

La scheda passa a online quando il software Rover, configurato per l'invio dei dati all'hub, riceve la prima conferma di acquisizione. Questa procedura prepara l'hub. Il collaudo sul Raspberry si esegue dopo l'installazione del codice Rover predisposto per l'invio.

La scheda usa l'ultimo campione di stato per posizione, ora GNSS, FIX e RTCM. L'ultimo evento rilevato può essere un indice missione. La posizione eventualmente rimasta in memoria resta associata al suo orario originale.

## Collegamento alla pagina diretta

Per aggiungere il collegamento, ripeti la registrazione con `--dashboard-url` seguito dall'URL diretto del Rover, per esempio `http://INDIRIZZO-ROVER:8080/autopilota.html`. Ometti `--output` se hai già creato il file di credenziali. Applica poi la configurazione al servizio web come sopra. Usa `--clear-dashboard-url` per rimuovere il collegamento.

Per il Rover attuale usa `http://100.73.187.83:8080/autopilota.html`. L'HP e il browser devono poter raggiungere questo indirizzo su Tailscale.

## Avvio su richiesta

Sul Raspberry aggiorna `/home/terminator/Documents/telemetry_server.py` e copia anche `deploy/systemd/` dal repository Rover. Prima di abilitare il socket, ferma l'eventuale istanza avviata manualmente o il vecchio servizio che occupa la porta 8080. Esegui l'installazione con il Rover fermo.

```bash
cd /home/terminator/Documents
sudo install -m 644 deploy/systemd/terminator-rover.{socket,service} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now terminator-rover.socket
```

Il socket è in ascolto sull'IP Tailscale del Rover. La prima connessione alla porta 8080 avvia `telemetry_server.py` con `BASE_TAILSCALE_HOST=100.85.248.82`. Il Rover legge le coordinate della Base da `GET /api/state`. Il servizio rimane in esecuzione dopo la chiusura della pagina. Se usi un indirizzo Tailscale diverso, aggiorna `ListenStream=` nel file socket e l'URL nell'hub. Il file di credenziali opzionale per l'invio eventi resta in `/home/terminator/.config/terminator/rover-01.env`.

Aggiorna anche l'hub sull'HP e ricostruiscilo con `bash hub/start-hub.sh`. Quando premi **Apri la pagina del Rover**, l'hub attende che la pagina risponda e poi la apre direttamente nel browser. Se il Rover è irraggiungibile, l'hub chiede di controllare alimentazione, connessione Internet e Tailscale. Se la porta risponde ma la pagina non è pronta, controlla sul Raspberry:

```bash
sudo systemctl status terminator-rover.socket terminator-rover.service
sudo journalctl -u terminator-rover.service -n 50 --no-pager
```

Per arrestare il servizio senza consentire un nuovo avvio su richiesta, ferma entrambe le unità con `sudo systemctl stop terminator-rover.socket terminator-rover.service`.
