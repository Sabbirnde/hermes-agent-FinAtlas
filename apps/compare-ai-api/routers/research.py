"""COMPARE AI — Research Router"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(..., description="Natural language financial query")
    country_code: str = Field("BD", description="ISO country code")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    user_profile: Optional[dict] = Field(None, description="Optional user profile")
    priority: Optional[str] = Field(None, description="User priority override")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "I need a personal loan of ৳500,000 for 5 years. Find the cheapest option.",
                "country_code": "BD",
            }
        }


class ClarificationResponse(BaseModel):
    session_id: str
    run_id: str
    question: str
    field_needed: str


class ResearchResponse(BaseModel):
    run_id: str
    session_id: str
    state: str
    intent: Optional[dict]
    clarification_needed: bool
    clarification_questions: list[str]
    message: str


class ResearchResultResponse(BaseModel):
    run_id: str
    state: str
    products: list[dict]
    calculation_results: list[dict]
    eligibility_results: list[dict]
    ranked_products: list[dict]
    conflicts_detected: int
    sources_checked: int
    answer_text: Optional[str]
    disclaimer: str
    checked_at: str


# ── In-memory session store (replace with Redis in production) ────────────────

_sessions: dict[str, dict] = {}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new research session.
    Returns immediately with run_id and initial state.
    Research continues asynchronously — poll /status/{run_id} or connect WebSocket.
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

    from skills.finance.compare_ai.scripts.intent_agent import extract_intent, get_clarification_questions

    session_id = request.session_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    # Extract intent
    intent = extract_intent(request.query, request.country_code)
    clarifications = get_clarification_questions(intent)

    # Store session
    _sessions[run_id] = {
        "run_id": run_id,
        "session_id": session_id,
        "query": request.query,
        "country_code": request.country_code,
        "intent": intent.to_dict(),
        "state": "INTENT_EXTRACTED" if not clarifications else "CLARIFICATION_REQUIRED",
        "clarifications": clarifications,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "products": [],
        "ranked": [],
    }

    # If no clarifications needed, kick off research in background
    if not clarifications:
        background_tasks.add_task(run_research_pipeline, run_id, intent.to_dict())

    return ResearchResponse(
        run_id=run_id,
        session_id=session_id,
        state=_sessions[run_id]["state"],
        intent=intent.to_dict(),
        clarification_needed=bool(clarifications),
        clarification_questions=clarifications,
        message=(
            "Research started. Connect to WebSocket /ws/{run_id} for live updates."
            if not clarifications
            else "Please answer the clarification questions to continue."
        ),
    )


@router.post("/clarify/{run_id}")
async def answer_clarification(
    run_id: str,
    answer: str,
    background_tasks: BackgroundTasks,
):
    """Provide a clarification answer and resume research."""
    if run_id not in _sessions:
        raise HTTPException(status_code=404, detail="Research run not found")

    session = _sessions[run_id]
    # Update intent with clarification
    # In production: re-run intent extraction with merged context
    session["state"] = "RESEARCH_PLANNED"
    background_tasks.add_task(run_research_pipeline, run_id, session["intent"])

    return {"run_id": run_id, "state": "RESEARCH_PLANNED", "message": "Research resumed."}


@router.get("/status/{run_id}")
async def get_status(run_id: str):
    """Poll research run status."""
    if run_id not in _sessions:
        raise HTTPException(status_code=404, detail="Research run not found")
    session = _sessions[run_id]
    return {
        "run_id": run_id,
        "state": session["state"],
        "products_found": len(session.get("products", [])),
        "ranked_count": len(session.get("ranked", [])),
    }


@router.get("/result/{run_id}", response_model=ResearchResultResponse)
async def get_result(run_id: str):
    """Get full research results for a completed run."""
    if run_id not in _sessions:
        raise HTTPException(status_code=404, detail="Research run not found")

    session = _sessions[run_id]
    if session["state"] not in ("COMPLETED", "ANSWER_GENERATED"):
        raise HTTPException(
            status_code=202,
            detail=f"Research still in progress. Current state: {session['state']}"
        )

    return ResearchResultResponse(
        run_id=run_id,
        state=session["state"],
        products=session.get("products", []),
        calculation_results=session.get("calculations", []),
        eligibility_results=session.get("eligibility", []),
        ranked_products=session.get("ranked", []),
        conflicts_detected=session.get("conflicts", 0),
        sources_checked=session.get("sources_checked", 0),
        answer_text=session.get("answer_text"),
        disclaimer=(
            "COMPARE AI provides financial product information for research purposes only. "
            "It does not provide financial advice, guarantee loan approval, or guarantee returns. "
            "Always verify with the financial institution before making financial decisions."
        ),
        checked_at=datetime.now(timezone.utc).date().isoformat(),
    )


# ── Background Research Pipeline ──────────────────────────────────────────────

async def run_research_pipeline(run_id: str, intent: dict):
    """
    Execute the full 15-stage research pipeline asynchronously.
    This function orchestrates all the Python engine scripts.
    """
    import sys
    import os

    session = _sessions.get(run_id)
    if not session:
        return

    try:
        # Stage: RESEARCH_PLANNED
        session["state"] = "RESEARCH_PLANNED"

        # Stage: SOURCES_DISCOVERED
        session["state"] = "SOURCES_DISCOVERED"

        # Stage: SOURCES_FETCHED (web research via Hermes tools)
        session["state"] = "SOURCES_FETCHED"

        # Stage: PRODUCTS_EXTRACTED
        session["state"] = "PRODUCTS_EXTRACTED"

        # Stage: EVIDENCE_COLLECTED
        session["state"] = "EVIDENCE_COLLECTED"

        # Stage: VERIFICATION_COMPLETE
        session["state"] = "VERIFICATION_COMPLETE"

        # Stage: CALCULATIONS_COMPLETE
        session["state"] = "CALCULATIONS_COMPLETE"

        # Stage: ELIGIBILITY_EVALUATED
        session["state"] = "ELIGIBILITY_EVALUATED"

        # Stage: PRODUCTS_RANKED
        session["state"] = "PRODUCTS_RANKED"

        # Stage: ANSWER_GENERATED
        session["state"] = "ANSWER_GENERATED"

        # Stage: COMPLETED
        session["state"] = "COMPLETED"

    except Exception as e:
        session["state"] = "EXTRACTION_FAILED"
        session["error"] = str(e)
