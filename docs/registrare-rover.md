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

Il link apre la pagina del Rover in una nuova scheda attraverso il collegamento diretto dal browser. Il collaudo della latenza richiede il Rover acceso.
