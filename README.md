# Hub Terminator per HP Linux

Questo repository contiene l'API, PostgreSQL e la dashboard per l'HP con Ubuntu. Per installare e collaudare l'hub con Rover e Base simulati, segui la [guida della fase 2](docs/fase-2-hub-ubuntu.md).

Per acquisire dati reali, segui la [guida per collegare la Base RTK](docs/collegare-base.md).

L'hub può [registrare un Rover e avviarne il servizio su richiesta](docs/registrare-rover.md#avvio-su-richiesta). Il pulsante **Apri la pagina del Rover** usa l'indirizzo Tailscale configurato durante la registrazione.

Per aggiornare un'installazione esistente, esegui questi comandi dalla radice del repository sull'HP.

```bash
git pull --ff-only
bash hub/start-hub.sh
```

Per creare l'icona **Avvia Hub Terminator** sul Desktop di Ubuntu, esegui una volta `bash hub/start-hub.sh --install-desktop` e abilita **Consenti avvio** dal menu dell'icona, se richiesto. L'icona usa la configurazione locale, mostra l'esito nel terminale e apre la dashboard in Firefox quando l'hub risponde.

La dashboard mostra **HP Ubuntu · Online** quando il servizio web risponde e riesce a leggere PostgreSQL. Se l'HP o il servizio è spento, la pagina non è raggiungibile. Per cambiare il nome della scheda, imposta `HUB_DISPLAY_NAME` nel file locale `hub/.env`.

La configurazione locale in `hub/.env` resta sull'HP. PostgreSQL conserva gli eventi nel volume Docker `pgdata`.

## Mappa condivisa

Il pulsante **Mappa** apre `/index.html` sull'HP. I perimetri condivisi sono salvati nel volume Docker `mapdata`. La mappa usa gli ultimi campioni di posizione ricevuti dall'Hub dal Rover e dalla Base. Le pagine operative del Rover restano accessibili tramite i loro indirizzi diretti. I perimetri della mappa condivisa sono per la visualizzazione e non sono inviati al Rover come geofence operativo.

Per aprire la mappa HP anche dall'index di Windows, imposta `hubMapUrl` nel suo `runtime-config.js` con l'URL HTTPS della dashboard restituito da `tailscale serve status`. Sul Rover, dopo aver aggiornato il software, viene riutilizzato `ROVER_HUB_URL` se già configurato. Altrimenti imposta `ROVER_MAP_HUB_URL` con lo stesso indirizzo HTTPS nel servizio del Rover. Se HP non risponde, l'index di partenza usa il suo archivio locale e la sua fonte di telemetria configurata. Per un file aperto direttamente su Windows, imposta anche `apiBaseUrl` per la Base oppure `roverWsUrl` con il WebSocket del Rover. Aggiungi `?locale=1` all'URL dell'index di partenza per aprire direttamente la copia locale.

Per recuperare perimetri già disegnati, apri l'index con `?locale=1` nello stesso browser e allo stesso indirizzo usati in precedenza. Premi **Esporta**, poi apri la mappa dall'Hub e usa **Importa su HP**. L'importazione aggiunge i poligoni e salta quelli con geometria identica. Ripeti dagli altri browser o indirizzi che contengono perimetri da conservare.

La copia `hub/index.html` permette di installare l'Hub in autonomia. Quando modifichi `static/index.html` nel repository Rover, aggiorna anche la copia nell'Hub prima di ricostruire l'immagine.

## Sviluppi futuri

Aggiungere un registro degli accessi separato dalle schede dei dispositivi. Partire dagli accessi alla dashboard dell'HP e registrare l'identità disponibile, il servizio e l'ora. In seguito, raccogliere gli eventi dai servizi del Rover e delle antenne per coprire anche gli accessi diretti. Definire chi può consultare il registro e per quanto tempo conservarlo. Guida e correzioni RTCM continuano a usare i loro collegamenti diretti.
