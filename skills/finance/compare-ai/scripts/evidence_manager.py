#!/usr/bin/env python3
"""
COMPARE AI — Evidence Manager

Tracks source evidence for every financial claim.
Every material financial field must have traceable evidence.

Usage:
    python3 evidence_manager.py reset
    python3 evidence_manager.py add --url URL --field interest_rate --value "12%" --evidence-text "..."
    python3 evidence_manager.py list
    python3 evidence_manager.py verify --product-id <id>
    python3 evidence_manager.py export --format json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field
import uuid

# Default ledger path (respects HERMES_HOME)
HERMES_HOME = os.environ.get(
    "HERMES_HOME",
    os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes")
)
DEFAULT_LEDGER = Path(HERMES_HOME) / "cache" / "compare-ai" / "evidence_ledger.json"


SOURCE_TIER_MAP = {
    "regulatory": 1,
    "central_bank": 1,
    "government": 1,
    "official_product_page": 2,
    "official_website": 2,
    "official_rate_sheet": 2,
    "official_fee_schedule": 2,
    "official_terms": 2,
    "official_pdf": 3,
    "official_circular": 3,
    "annual_report": 3,
    "product_brochure": 3,
    "financial_publication": 4,
    "news": 4,
    "forum": 5,
    "social_media": 5,
    "unknown": 0,
}

CONFIDENCE_BY_TIER = {1: 0.97, 2: 0.90, 3: 0.80, 4: 0.60, 5: 0.20, 0: 0.30}

MATERIAL_FIELDS = {
    "interest_rate", "profit_rate", "annual_rate", "rate_type",
    "loan_amount_min", "loan_amount_max", "tenure_min", "tenure_max",
    "processing_fee", "prepayment_fee", "documentation_fee",
    "collateral_required", "eligibility_age_min", "eligibility_age_max",
    "eligibility_income_min", "eligibility_employment",
    "deposit_rate", "fdr_rate", "dps_rate",
    "min_deposit", "max_deposit", "payout_frequency",
    "premature_withdrawal", "lock_in_months",
}


@dataclass
class EvidenceRecord:
    record_id: str
    product_id: str
    institution_name: str
    product_name: str
    country_code: str
    field_name: str
    field_value: Optional[str]
    source_url: str
    source_type: str
    source_tier: int
    evidence_text: str
    page_number: Optional[int]
    checked_at: str
    published_at: Optional[str]
    freshness_status: str
    verification_status: str
    confidence_score: float
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class EvidenceLedger:
    def __init__(self, ledger_path: Optional[Path] = None):
        self.path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, EvidenceRecord] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for rec in data.get("records", []):
                    r = EvidenceRecord(**rec)
                    self._records[r.record_id] = r
            except Exception:
                self._records = {}

    def _save(self):
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "records": [r.to_dict() for r in self._records.values()],
        }
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(
        self,
        product_id: str,
        institution_name: str,
        product_name: str,
        country_code: str,
        field_name: str,
        field_value: Optional[str],
        source_url: str,
        source_type: str,
        evidence_text: str,
        page_number: Optional[int] = None,
        published_at: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> EvidenceRecord:
        """Add a new evidence record. Returns the record."""
        tier = SOURCE_TIER_MAP.get(source_type, 0)
        confidence = CONFIDENCE_BY_TIER.get(tier, 0.30)
        now = datetime.now(timezone.utc).date().isoformat()

        # Freshness
        freshness = "unknown"
        if published_at:
            try:
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
                today = datetime.now(timezone.utc).date()
                days_old = (today - pub_date).days
                if days_old <= 30:
                    freshness = "fresh"
                elif days_old <= 90:
                    freshness = "recent"
                else:
                    freshness = "stale"
            except Exception:
                freshness = "unknown"

        record = EvidenceRecord(
            record_id=str(uuid.uuid4()),
            product_id=product_id,
            institution_name=institution_name,
            product_name=product_name,
            country_code=country_code,
            field_name=field_name,
            field_value=field_value,
            source_url=source_url,
            source_type=source_type,
            source_tier=tier,
            evidence_text=evidence_text,
            page_number=page_number,
            checked_at=now,
            published_at=published_at,
            freshness_status=freshness,
            verification_status="verified",
            confidence_score=confidence,
            notes=notes,
        )
        self._records[record.record_id] = record
        self._save()
        return record

    def get_by_product(self, product_id: str) -> list[EvidenceRecord]:
        return [r for r in self._records.values() if r.product_id == product_id]

    def get_by_field(self, product_id: str, field_name: str) -> list[EvidenceRecord]:
        return [
            r for r in self._records.values()
            if r.product_id == product_id and r.field_name == field_name
        ]

    def list_all(self) -> list[EvidenceRecord]:
        return list(self._records.values())

    def reset(self):
        self._records = {}
        self._save()

    def coverage_report(self, product_id: str) -> dict:
        """Check evidence coverage for material fields."""
        records = self.get_by_product(product_id)
        covered_fields = {r.field_name for r in records}
        missing = MATERIAL_FIELDS - covered_fields
        coverage_pct = len(covered_fields & MATERIAL_FIELDS) / len(MATERIAL_FIELDS) * 100

        return {
            "product_id": product_id,
            "covered_fields": sorted(covered_fields & MATERIAL_FIELDS),
            "missing_fields": sorted(missing),
            "coverage_pct": round(coverage_pct, 1),
            "total_records": len(records),
        }

    def export_json(self) -> str:
        return json.dumps(
            [r.to_dict() for r in self._records.values()],
            indent=2, ensure_ascii=False
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="COMPARE AI Evidence Manager")
    parser.add_argument("--ledger", help="Custom ledger path")
    subparsers = parser.add_subparsers(dest="command")

    # reset
    subparsers.add_parser("reset", help="Clear all evidence records")

    # add
    add_p = subparsers.add_parser("add", help="Add evidence record")
    add_p.add_argument("--product-id", required=True)
    add_p.add_argument("--institution", required=True)
    add_p.add_argument("--product-name", required=True)
    add_p.add_argument("--country", default="BD")
    add_p.add_argument("--field", required=True)
    add_p.add_argument("--value", required=True)
    add_p.add_argument("--url", required=True)
    add_p.add_argument("--source-type", default="official_product_page")
    add_p.add_argument("--evidence-text", required=True)
    add_p.add_argument("--page", type=int)
    add_p.add_argument("--published-at")
    add_p.add_argument("--notes")

    # list
    list_p = subparsers.add_parser("list", help="List evidence records")
    list_p.add_argument("--product-id")
    list_p.add_argument("--json", action="store_true")

    # verify (coverage check)
    ver_p = subparsers.add_parser("verify", help="Check evidence coverage")
    ver_p.add_argument("--product-id", required=True)

    # export
    exp_p = subparsers.add_parser("export", help="Export all evidence")
    exp_p.add_argument("--format", default="json")

    args = parser.parse_args()
    ledger = EvidenceLedger(args.ledger if args.ledger else None)

    if args.command == "reset":
        ledger.reset()
        print("✓ Evidence ledger reset.")

    elif args.command == "add":
        record = ledger.add(
            product_id=args.product_id,
            institution_name=args.institution,
            product_name=args.product_name,
            country_code=args.country,
            field_name=args.field,
            field_value=args.value,
            source_url=args.url,
            source_type=args.source_type,
            evidence_text=args.evidence_text,
            page_number=args.page,
            published_at=args.published_at,
            notes=args.notes,
        )
        print(f"✓ Evidence added: {record.record_id}")
        print(f"  Field:       {record.field_name} = {record.field_value}")
        print(f"  Source:      Tier {record.source_tier} ({record.source_type})")
        print(f"  Confidence:  {record.confidence_score:.0%}")
        print(f"  Freshness:   {record.freshness_status}")

    elif args.command == "list":
        records = ledger.get_by_product(args.product_id) if args.product_id else ledger.list_all()
        if getattr(args, "json", False):
            print(json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False))
        else:
            print(f"\n── Evidence Records ({len(records)}) ─────────────────────────")
            for r in records:
                print(f"  [{r.source_tier}] {r.field_name}: {r.field_value}")
                print(f"      Source: {r.source_url}")
                print(f"      Evidence: \"{r.evidence_text[:80]}...\"" if len(r.evidence_text) > 80
                      else f"      Evidence: \"{r.evidence_text}\"")
                print(f"      Checked: {r.checked_at} | Confidence: {r.confidence_score:.0%} | Freshness: {r.freshness_status}")
                print()

    elif args.command == "verify":
        report = ledger.coverage_report(args.product_id)
        print(f"\n── Evidence Coverage: {args.product_id} ─────────────────")
        print(f"  Coverage:       {report['coverage_pct']}%")
        print(f"  Total records:  {report['total_records']}")
        print(f"  Covered fields: {', '.join(report['covered_fields']) or 'none'}")
        if report["missing_fields"]:
            print(f"  Missing fields: {', '.join(report['missing_fields'])}")

    elif args.command == "export":
        print(ledger.export_json())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
