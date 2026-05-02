from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from wavehome.gesture_catalog import GESTURE_CATALOG
from wavehome.workflow.catalog import workflow_catalog
from wavehome.workflow.loader import load_rules, save_rules
from wavehome.workflow.presets import get_rule_presets
from wavehome.workflow.schema import RuleValidationError

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="waveHome Dashboard API")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/capabilities")
def capabilities():
    catalog = workflow_catalog()
    catalog["gestures"] = GESTURE_CATALOG
    return catalog


@app.get("/api/gestures")
def gestures():
    return GESTURE_CATALOG


@app.get("/api/presets")
def presets():
    return get_rule_presets()


@app.get("/api/rules")
def rules():
    return load_rules()


@app.put("/api/rules")
def update_rules(config: dict):
    try:
        return save_rules(config)
    except RuleValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
