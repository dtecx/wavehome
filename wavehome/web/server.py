from fastapi import FastAPI

from wavehome.gesture_catalog import GESTURE_CATALOG
from wavehome.workflow.loader import load_rules


app = FastAPI(title="waveHome Dashboard API")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/gestures")
def gestures():
    return GESTURE_CATALOG


@app.get("/api/rules")
def rules():
    return load_rules()
