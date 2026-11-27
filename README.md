# Hub Terminator per HP Linux

Questo repository contiene l'API, PostgreSQL e la dashboard per l'HP con Ubuntu. Per installare e collaudare l'hub con Rover e Base simulati, segui la [guida della fase 2](docs/fase-2-hub-ubuntu.md).

Per acquisire dati reali, segui la [guida per collegare la Base RTK](docs/collegare-base.md).

L'hub può anche [registrare un Rover](docs/registrare-rover.md) e assegnargli un token dedicato.

Per aggiornare un'installazione esistente, esegui questi comandi dalla radice del repository sull'HP.

```bash
git pull --ff-only
bash hub/start-hub.sh
```

Per creare l'icona **Avvia Hub Terminator** sul Desktop di Ubuntu, esegui una volta `bash hub/start-hub.sh --install-desktop` e abilita **Consenti avvio** dal menu dell'icona, se richiesto. L'icona usa la configurazione locale, mostra l'esito nel terminale e apre la dashboard in Firefox quando l'hub risponde.

La dashboard mostra **HP Ubuntu · Online** quando il servizio web risponde e riesce a leggere PostgreSQL. Se l'HP o il servizio è spento, la pagina non è raggiungibile. Per cambiare il nome della scheda, imposta `HUB_DISPLAY_NAME` nel file locale `hub/.env`.

La configurazione locale in `hub/.env` resta sull'HP. PostgreSQL conserva gli eventi nel volume Docker `pgdata`.

## Sviluppi futuri

Aggiungere un registro degli accessi separato dalle schede dei dispositivi. Partire dagli accessi alla dashboard dell'HP e registrare l'identità disponibile, il servizio e l'ora. In seguito, raccogliere gli eventi dai servizi del Rover e delle antenne per coprire anche gli accessi diretti. Definire chi può consultare il registro e per quanto tempo conservarlo. Guida e correzioni RTCM continuano a usare i loro collegamenti diretti.
