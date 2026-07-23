# SDP Explorer

Interactive feature demonstrations for **Lakeflow Spark Declarative Pipelines (SDP)** — a more intuitive, visual companion to the docs, packaged as a Databricks App. Built by Field Engineering to scale SDP adoption.

Each SDP feature is a browsable card whose hero is an **animation of what the feature does to your data**, followed by the SQL/Python and an honest "when to leverage / watch out" digest. It is a self-contained teaching app: a small FastAPI server serving one static HTML/JS file — no notebooks, datasets, or pipelines are provisioned, and all sample data shown is **synthetic and generated in-browser**.

Cards covered include: Streaming Tables, Materialized Views, Enzyme incremental refresh, AUTO CDC (SCD1/2, from-snapshot, bitemporal), Append flows, REPLACE WHERE, Expectations, Quarantine, Sinks, Row filters & column masks, Liquid clustering, Private datasets, Watermarks, Real-time mode, Rewind & Replay, and CI/CD with Databricks Asset Bundles.

## Video Overview

The **Rewind & Replay** card in action: drag the rewind point T (the chips and cost meter react live), then run the recovery and watch the pipeline roll back its checkpoint, restore the target table, and replay only the affected batches instead of a full refresh.

![Rewind & Replay card demo](docs/rewind-replay.gif)

## Installation

Run locally:

```bash
pip install -r requirements.txt
python app.py            # serves on http://localhost:8000
```

Deploy to Databricks Apps via Asset Bundle (recommended):

```bash
databricks bundle deploy --profile <PROFILE>
databricks bundle run sdp-explorer --profile <PROFILE>
```

Or via the Apps CLI directly:

```bash
databricks apps create sdp-explorer --profile <PROFILE>
databricks sync . "/Workspace/Users/<you>/sdp-explorer" --profile <PROFILE>
databricks apps deploy sdp-explorer \
  --source-code-path "/Workspace/Users/<you>/sdp-explorer" --profile <PROFILE>
```

Project layout:

```
sdp-explorer/
├── app.py            # FastAPI static server (binds 0.0.0.0:$DATABRICKS_APP_PORT)
├── app.yaml          # Databricks Apps runtime command
├── databricks.yml    # Asset Bundle deployment config
├── requirements.txt  # fastapi + uvicorn
└── static/
    ├── index.html    # the app — all cards, styles, and animation logic in one file
    ├── gsap.min.js   # vendored GSAP 3.12.7 (animation, no CDN)
    ├── gsap-flip.min.js
    └── databricks-logo.svg
```

## How to get help

Databricks support doesn't cover this content. For questions or bugs, please open a GitHub issue and the team will help on a best effort basis.

## License

&copy; 2026 Databricks, Inc. All rights reserved. The source in this project is provided subject to the Databricks License [https://databricks.com/db-license-source]. All included or referenced third party libraries are subject to the licenses set forth below.

| library      | description                         | license                                | source                                         |
|--------------|-------------------------------------|----------------------------------------|------------------------------------------------|
| FastAPI      | Python web framework (app server)   | MIT                                    | https://github.com/fastapi/fastapi             |
| Uvicorn      | ASGI server                         | BSD-3-Clause                           | https://github.com/encode/uvicorn              |
| GSAP         | Animation engine (vendored, 3.12.7) | GreenSock Standard "No Charge" License | https://gsap.com/community/standard-license/   |
| DM Sans      | Web font (loaded from Google Fonts) | SIL Open Font License 1.1              | https://fonts.google.com/specimen/DM+Sans      |
| Martian Mono | Web font (loaded from Google Fonts) | SIL Open Font License 1.1              | https://fonts.google.com/specimen/Martian+Mono |
