from __future__ import annotations

from fastapi import FastAPI, HTTPException

from wavehome.gesture_catalog import GESTURE_CATALOG
from wavehome.workflow.loader import load_rules, save_rules
from wavehome.workflow.schema import (
    ACTION_KINDS,
    TRIGGER_KINDS,
    RuleValidationError,
)


app = FastAPI(title="waveHome Dashboard API")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/capabilities")
def capabilities():
    return {
        "gestures": GESTURE_CATALOG,
        "trigger_kinds": sorted(TRIGGER_KINDS),
        "action_kinds": sorted(ACTION_KINDS),
        "safety_blocks": [
            "cooldown",
            "confirmation",
            "command_mode",
            "min_confidence",
            "max_total_time",
            "max_step_gap",
        ],
    }


@app.get("/api/gestures")
def gestures():
    return GESTURE_CATALOG


@app.get("/api/rules")
def rules():
    return load_rules()


@app.put("/api/rules")
def update_rules(config: dict):
    try:
        return save_rules(config)
    except RuleValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
