# Collegare la Base RTK reale

Il servizio opzionale `base` legge `GET /api/state` dall'antenna ogni 10 secondi circa. Registra nell'hub soltanto la parte Base. L'identità è `base-rtk-01`, separata dai dispositivi simulati. L'ora della posizione proviene dalla Base, mentre l'ora di ricezione viene assegnata dall'hub.

Il servizio gira sull'HP e usa l'API HTTP già disponibile sulla rete privata. Rover e flusso RTCM possono continuare a usare la configurazione esistente. Il servizio acquisisce istantanee correnti. La sincronizzazione degli eventi con coda durevole sui dispositivi resta un passaggio successivo.

## Avvio

Parti da un hub già collaudato con la [demo](fase-2-hub-ubuntu.md). Dalla cartella `hub` sull'HP esegui i comandi seguenti e sostituisci `INDIRIZZO_BASE` con l'indirizzo Tailscale dell'antenna.

```bash
python3 setup_base.py http://INDIRIZZO_BASE:8080/api/state
sudo docker compose --profile base up -d --build --wait
sudo docker compose logs --tail 15 base
```

Il primo comando aggiunge la Base al file locale `.env` e conserva i token già configurati. Dopo il primo invio riuscito, il log mostra `Stato Base salvato nell'hub`. Apri la [dashboard sull'HP](http://127.0.0.1:8090/) e controlla che la scheda `base-rtk-01` sia online. L'assenza di qualità GGA può dipendere dalla provenienza della posizione e viene mostrata come `Non riportata`.

Se la lettura fallisce, verifica che il container possa raggiungere l'API della Base attraverso Tailscale. Dopo la soglia configurata senza eventi, la dashboard mostra la Base offline e conserva l'ultima posizione con il suo orario.

Una volta abilitato il profilo, usa `sudo docker compose --profile base up -d --build --wait` anche per gli aggiornamenti.

## Rimuovere le schede simulate

Quando `base-rtk-01` è online, riesegui `setup_base.py` con lo stesso URL e aggiungi `--remove-demo`. Poi applica la configurazione con `sudo docker compose --profile base up -d --wait`. Le identità demo e i relativi token escono dalla configurazione attiva. Gli eventi già acquisiti restano nel database.

Per aprire la stessa dashboard da un altro PC, segui la [procedura Tailscale Serve](fase-2-hub-ubuntu.md#accesso-da-windows).
