# lbh-quick-wins
A website containing various automations to be used internally at the LBH Group

## Running with Docker

Before starting the container, two files must exist locally (both are gitignored, so they
are never bundled into the Docker image and must be supplied per-deployment):

- `.streamlit/secrets.toml` — SMTP credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
  `SMTP_PASSWORD`, `MAIL_FROM`).
- `src/quick_wins/config/crowdstrike_config.json` — per-unit routing config and recipient
  emails.

Then build and run:

```bash
docker compose up --build
```

The app is served at [http://localhost:8501](http://localhost:8501).
