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

### Sharing the Crowdstrike vulnerability history across colleagues

Each Crowdstrike zip upload appends per-country Critical/High counts to
`data/crowdstike/vulnerability_history.csv`, which powers the trendline chart.
By default this file is purely local to your machine. To make it a shared
source of truth across everyone running the app, point it at a SharePoint
library synced via OneDrive:

1. Copy `.env.example` to `.env` (gitignored, never uploaded to GitHub).
2. Follow the steps in `.env.example` to sync the SharePoint library and set
   `CROWDSTRIKE_HISTORY_DIR` to its local synced path.
3. Restart with `docker compose up --build --force-recreate`.

Since this relies on OneDrive's background sync rather than real-time
locking, two people uploading within the same few seconds can occasionally
produce a sync conflict copy of the CSV that needs manual merging - this is
a known tradeoff of the synced-folder approach, not a bug.
