#!/usr/bin/env python3
"""
COMPARE AI — Research State Machine

Manages the 15-stage research pipeline state and produces full audit traces.

States:
    RECEIVED → INTENT_EXTRACTED → CLARIFICATION_REQUIRED →
    RESEARCH_PLANNED → SOURCES_DISCOVERED → SOURCES_FETCHED →
    PRODUCTS_EXTRACTED → EVIDENCE_COLLECTED → VERIFICATION_COMPLETE →
    CALCULATIONS_COMPLETE → ELIGIBILITY_EVALUATED → PRODUCTS_RANKED →
    ANSWER_GENERATED → COMPLETED

    Failure: INSUFFICIENT_SOURCES | SOURCE_UNAVAILABLE | CONFLICTING_INFORMATION |
             EXTRACTION_FAILED | CALCULATION_FAILED | VERIFICATION_FAILED
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


STATES = [
    "RECEIVED",
    "INTENT_EXTRACTED",
    "CLARIFICATION_REQUIRED",
    "RESEARCH_PLANNED",
    "SOURCES_DISCOVERED",
    "SOURCES_FETCHED",
    "PRODUCTS_EXTRACTED",
    "EVIDENCE_COLLECTED",
    "VERIFICATION_COMPLETE",
    "CALCULATIONS_COMPLETE",
    "ELIGIBILITY_EVALUATED",
    "PRODUCTS_RANKED",
    "ANSWER_GENERATED",
    "COMPLETED",
]

FAILURE_STATES = [
    "INSUFFICIENT_SOURCES",
    "SOURCE_UNAVAILABLE",
    "CONFLICTING_INFORMATION",
    "EXTRACTION_FAILED",
    "CALCULATION_FAILED",
    "VERIFICATION_FAILED",
]

HERMES_HOME = os.environ.get(
    "HERMES_HOME",
    os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes")
)
RUNS_DIR = Path(HERMES_HOME) / "cache" / "compare-ai" / "research_runs"


@dataclass
class StateTransition:
    from_state: str
    to_state: str
    timestamp: str
    notes: Optional[str] = None
    data: Optional[dict] = None


@dataclass
class ResearchRun:
    run_id: str
    session_id: str
    country_code: str
    user_query: str
    state: str
    created_at: str
    updated_at: str

    # Pipeline data
    intent: Optional[dict] = None
    research_plan: Optional[dict] = None
    sources_discovered: list = field(default_factory=list)
    sources_visited: list = field(default_factory=list)
    sources_accepted: list = field(default_factory=list)
    sources_rejected: dict = field(default_factory=dict)
    products_extracted: list = field(default_factory=list)
    evidence_records: list = field(default_factory=list)
    verification_results: dict = field(default_factory=dict)
    calculation_results: list = field(default_factory=list)
    eligibility_results: list = field(default_factory=list)
    ranked_products: list = field(default_factory=list)
    final_answer: Optional[str] = None

    # Observability
    state_transitions: list = field(default_factory=list)
    search_queries: list = field(default_factory=list)
    conflicts_detected: int = 0
    total_llm_cost_usd: float = 0.0
    execution_ms: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def add_transition(self, to_state: str, notes: Optional[str] = None, data: Optional[dict] = None):
        transition = StateTransition(
            from_state=self.state,
            to_state=to_state,
            timestamp=datetime.now(timezone.utc).isoformat(),
            notes=notes,
            data=data,
        )
        self.state_transitions.append(asdict(transition))
        self.state = to_state
        self.updated_at = datetime.now(timezone.utc).isoformat()


class ResearchStateMachine:
    def __init__(self, run_id: Optional[str] = None, session_id: Optional[str] = None):
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()

        if run_id:
            self.run = self._load(run_id)
        else:
            self.run = ResearchRun(
                run_id=str(uuid.uuid4()),
                session_id=session_id or str(uuid.uuid4()),
                country_code="BD",
                user_query="",
                state="RECEIVED",
                created_at=now,
                updated_at=now,
            )

    def _load(self, run_id: str) -> ResearchRun:
        path = RUNS_DIR / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Research run not found: {run_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ResearchRun(**data)

    def save(self):
        path = RUNS_DIR / f"{self.run.run_id}.json"
        path.write_text(
            json.dumps(self.run.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def transition(self, to_state: str, notes: Optional[str] = None, data: Optional[dict] = None):
        """Transition to next state. Raises if invalid."""
        if to_state not in STATES + FAILURE_STATES:
            raise ValueError(f"Unknown state: {to_state}")
        self.run.add_transition(to_state, notes, data)
        self.save()
        return self

    def fail(self, failure_state: str, error_message: str):
        """Transition to a failure state."""
        assert failure_state in FAILURE_STATES, f"Not a failure state: {failure_state}"
        self.run.error_message = error_message
        self.run.add_transition(failure_state, error_message)
        self.save()
        return self

    def status(self) -> dict:
        return {
            "run_id": self.run.run_id,
            "state": self.run.state,
            "country": self.run.country_code,
            "query": self.run.user_query,
            "sources_discovered": len(self.run.sources_discovered),
            "sources_accepted": len(self.run.sources_accepted),
            "products_found": len(self.run.products_extracted),
            "conflicts": self.run.conflicts_detected,
            "transitions": len(self.run.state_transitions),
            "last_updated": self.run.updated_at,
            "error": self.run.error_message,
        }

    def observability_trace(self) -> dict:
        """Full audit trace for this research run."""
        return {
            "research_id": self.run.run_id,
            "user_query": self.run.user_query,
            "intent": self.run.intent,
            "search_queries": self.run.search_queries,
            "sources_visited": self.run.sources_visited,
            "sources_accepted": self.run.sources_accepted,
            "sources_rejected": self.run.sources_rejected,
            "products_found": self.run.products_extracted,
            "evidence": self.run.evidence_records,
            "conflicts": self.run.conflicts_detected,
            "calculations": self.run.calculation_results,
            "eligibility": self.run.eligibility_results,
            "ranking": self.run.ranked_products,
            "final_state": self.run.state,
            "total_llm_cost_usd": self.run.total_llm_cost_usd,
            "execution_ms": self.run.execution_ms,
            "state_transitions": self.run.state_transitions,
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="COMPARE AI Research State Machine")
    parser.add_argument("--run-id", help="Existing run ID")
    parser.add_argument("--status", action="store_true", help="Show run status")
    parser.add_argument("--trace", action="store_true", help="Show full observability trace")
    parser.add_argument("--list", action="store_true", help="List all runs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        runs = sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        print(f"\n── Research Runs ({len(runs)}) ─────────────────────────────")
        for r in runs[:20]:
            data = json.loads(r.read_text(encoding="utf-8"))
            print(f"  {data['run_id'][:8]}... | {data['state']:30} | {data.get('user_query', '')[:50]}")
        return

    if not args.run_id:
        print("Provide --run-id or --list")
        return

    sm = ResearchStateMachine(run_id=args.run_id)

    if args.trace:
        trace = sm.observability_trace()
        if args.json:
            print(json.dumps(trace, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(trace, indent=2, ensure_ascii=False))
    elif args.status:
        status = sm.status()
        if args.json:
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print(f"\n── Research Run Status ──────────────────────────────────")
            for k, v in status.items():
                print(f"  {k:25} {v}")


if __name__ == "__main__":
    main()
