"""SDP Explorer — static site server for Databricks Apps.

Serves the interactive feature demonstrations (single-page static site under
static/). Binds to 0.0.0.0 on the platform-assigned DATABRICKS_APP_PORT.
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="SDP Explorer")

# Serve the static site at the root. html=True returns index.html for "/".
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
