# Hub Terminator per HP Linux

Questo repository contiene l'API, PostgreSQL e la dashboard per l'HP con Ubuntu. Per installare e collaudare l'hub con Rover e Base simulati, segui la [guida della fase 2](docs/fase-2-hub-ubuntu.md).

Per acquisire dati reali, segui la [guida per collegare la Base RTK](docs/collegare-base.md).

L'hub può anche [registrare un Rover](docs/registrare-rover.md) e assegnargli un token dedicato.

Per aggiornare un'installazione esistente, esegui questi comandi dalla radice del repository sull'HP.

```bash
git pull --ff-only
cd hub
sudo docker compose up -d --build --wait
```

La configurazione locale in `hub/.env` resta sull'HP. PostgreSQL conserva gli eventi nel volume Docker `pgdata`.
