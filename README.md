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

Il pulsante **Mappa** apre `/index.html` sull'HP. I perimetri e le preferenze di visibilita dei widget sono salvati nel volume Docker `mapdata`. La mappa usa gli ultimi campioni di posizione ricevuti dall'Hub dal Rover e dalla Base. Le pagine operative del Rover restano accessibili tramite i loro indirizzi diretti. I perimetri della mappa condivisa sono per la visualizzazione e non sono inviati al Rover come geofence operativo.

Per aprire la mappa HP anche dall'index di Windows, imposta `hubMapUrl` nel suo `runtime-config.js` con l'URL HTTPS della dashboard restituito da `tailscale serve status`. Sul Rover, dopo aver aggiornato il software, viene riutilizzato `ROVER_HUB_URL` se già configurato. Altrimenti imposta `ROVER_MAP_HUB_URL` con lo stesso indirizzo HTTPS nel servizio del Rover. Se HP non risponde, l'index di partenza usa il suo archivio locale e la sua fonte di telemetria configurata. Per un file aperto direttamente su Windows, imposta anche `apiBaseUrl` per la Base oppure `roverWsUrl` con il WebSocket del Rover. Aggiungi `?locale=1` all'URL dell'index di partenza per aprire direttamente la copia locale.

Per recuperare perimetri già disegnati, apri l'index con `?locale=1` nello stesso browser e allo stesso indirizzo usati in precedenza. Premi **Esporta**, poi apri la mappa dall'Hub e usa **Importa su HP**. L'importazione aggiunge i poligoni e salta quelli con geometria identica. Ripeti dagli altri browser o indirizzi che contengono perimetri da conservare.

Le copie `hub/index.html` e `hub/impostazioni_widgets.html` permettono di installare l'Hub in autonomia. Quando modifichi queste pagine nella cartella `static` del Rover, aggiorna anche le copie nell'Hub prima di ricostruire l'immagine.

## Analisi Scatter

Dalla Mappa Live, apri **Scatter Analysis**. L'HP serve la schermata e legge da PostgreSQL i campioni GNSS inviati dal Rover registrato all'Hub. **Avvia** mostra i fix ricevuti durante l'analisi. **Ultimi 15 minuti** mostra i fix che l'Hub ha già ricevuto, anche a Rover spento. Interpreta la dispersione solo quando il Rover era fermo. L'invio di stato all'Hub avviene normalmente ogni 10 secondi.

Il collettore Base invia la posizione di riferimento. Per il grafico Base serve una serie di misure GNSS con timestamp di fix. La pagina servita direttamente dal Rover mantiene il WebSocket locale. Aggiorna anche `hub/scatter_analysis.html` quando cambi la copia `static/scatter_analysis.html` nel Rover.

## Vigneto e Registrazioni

**Vigneto** apre il rilievo servito dall'HP. Puoi caricare il primo poligono della Mappa Live come copia di lavoro e analizzare le tessere satellitari nel browser. Il rilievo si esporta in JSON. Per generare il mondo Webots, importa il rilievo nella pagina del server locale sul PC.

**Registrazioni** mostra l'archivio delle missioni sull'HP. Dopo aver aggiornato l'Hub e il software Rover, accendi il Rover, selezionalo e premi **Sincronizza nuove missioni**. L'Hub usa l'indirizzo del Rover configurato durante la registrazione e copia i nuovi file JSON da `missions/`. La sincronizzazione si può ripetere per aggiungere registrazioni successive. Le copie sono identificate da Rover e nome del file e rimangono disponibili nel volume Docker `mapdata`, anche a Rover spento. L'anteprima usa le coordinate registrate e il tasto **Scarica JSON** scarica la missione completa.

Quando modifichi `registrazioni.html` o `vineyard.js` sul Rover, aggiorna anche le copie nella cartella `hub`.

## Sviluppi futuri

Aggiungere un registro degli accessi separato dalle schede dei dispositivi. Partire dagli accessi alla dashboard dell'HP e registrare l'identità disponibile, il servizio e l'ora. In seguito, raccogliere gli eventi dai servizi del Rover e delle antenne per coprire anche gli accessi diretti. Definire chi può consultare il registro e per quanto tempo conservarlo. Guida e correzioni RTCM continuano a usare i loro collegamenti diretti.
