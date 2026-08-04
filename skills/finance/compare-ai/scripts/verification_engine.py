#!/usr/bin/env python3
"""
COMPARE AI — Verification Engine + Conflict Detector

Verifies financial claims across multiple sources.
Detects and flags conflicts — NEVER silently resolves them.

Usage:
    python3 verification_engine.py --products-file products.json
    python3 verification_engine.py --field interest_rate --values '["10%","11%"]' --sources '["url1","url2"]'
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional
import re


@dataclass
class VerificationResult:
    field_name: str
    status: str          # verified | partial | unverified | conflicting | stale | unknown
    primary_value: Optional[str]
    primary_source: Optional[str]
    primary_tier: int
    confidence_score: float
    conflicts: list      # list of conflict dicts if conflicting
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConflictRecord:
    field_name: str
    source_a_url: str
    source_a_value: str
    source_a_tier: int
    source_b_url: str
    source_b_value: str
    source_b_tier: int
    conflict_type: str   # "value_mismatch" | "rate_mismatch" | "eligibility_mismatch"
    resolution: str      # "unresolved" | "prefer_higher_tier" | "prefer_newer"
    resolution_notes: str

    def to_dict(self) -> dict:
        return asdict(self)


SOURCE_TIER_MAP = {
    "regulatory": 1, "central_bank": 1, "government": 1,
    "official_product_page": 2, "official_website": 2,
    "official_rate_sheet": 2, "official_fee_schedule": 2,
    "official_pdf": 3, "official_circular": 3, "annual_report": 3,
    "financial_publication": 4, "news": 4,
    "forum": 5, "social_media": 5, "unknown": 0,
}

CONFIDENCE_BY_TIER = {1: 0.97, 2: 0.90, 3: 0.80, 4: 0.60, 5: 0.20, 0: 0.30}


def normalize_rate(value: str) -> Optional[float]:
    """Extract numeric rate from string like '12%', '12.5% p.a.', '12.5 percent'."""
    if value is None:
        return None
    m = re.search(r'([\d.]+)', str(value))
    if m:
        return float(m.group(1))
    return None


def values_conflict(val_a: str, val_b: str, field_name: str) -> bool:
    """Determine if two values conflict for a given field."""
    if val_a is None or val_b is None:
        return False

    # For rate fields, compare numerically with tolerance
    if any(kw in field_name for kw in ["rate", "fee", "amount", "income", "age"]):
        num_a = normalize_rate(val_a)
        num_b = normalize_rate(val_b)
        if num_a is not None and num_b is not None:
            # Allow 0.01% tolerance for floating point
            return abs(num_a - num_b) > 0.01
        # If we can't parse both, they might conflict
        return val_a.strip().lower() != val_b.strip().lower()

    # For text fields, simple string comparison
    return val_a.strip().lower() != val_b.strip().lower()


def verify_field(
    field_name: str,
    source_records: list[dict],
) -> VerificationResult:
    """
    Verify a single field across multiple source records.
    Each source_record: {url, value, source_type, checked_at, published_at}
    """
    if not source_records:
        return VerificationResult(
            field_name=field_name,
            status="unknown",
            primary_value=None,
            primary_source=None,
            primary_tier=0,
            confidence_score=0.0,
            conflicts=[],
            notes="No sources found for this field.",
        )

    # Sort by tier (lower = more authoritative), then by date
    def sort_key(rec):
        tier = SOURCE_TIER_MAP.get(rec.get("source_type", "unknown"), 0)
        return (tier, rec.get("checked_at", ""))

    sorted_records = sorted(source_records, key=sort_key)
    primary = sorted_records[0]
    primary_tier = SOURCE_TIER_MAP.get(primary.get("source_type", "unknown"), 0)

    # Conflict detection
    conflicts = []
    for i, rec_a in enumerate(sorted_records):
        for rec_b in sorted_records[i + 1:]:
            if values_conflict(rec_a.get("value"), rec_b.get("value"), field_name):
                tier_a = SOURCE_TIER_MAP.get(rec_a.get("source_type", "unknown"), 0)
                tier_b = SOURCE_TIER_MAP.get(rec_b.get("source_type", "unknown"), 0)

                # Resolution attempt: prefer lower tier (more authoritative)
                if tier_a < tier_b:
                    resolution = "prefer_higher_tier_source"
                    res_notes = f"Preferring Tier {tier_a} ({rec_a.get('source_type')}) over Tier {tier_b}"
                elif tier_b < tier_a:
                    resolution = "prefer_higher_tier_source"
                    res_notes = f"Preferring Tier {tier_b} ({rec_b.get('source_type')}) over Tier {tier_a}"
                else:
                    resolution = "unresolved"
                    res_notes = "Same-tier sources conflict. Manual verification required."

                conflicts.append(ConflictRecord(
                    field_name=field_name,
                    source_a_url=rec_a.get("url", ""),
                    source_a_value=str(rec_a.get("value", "")),
                    source_a_tier=tier_a,
                    source_b_url=rec_b.get("url", ""),
                    source_b_value=str(rec_b.get("value", "")),
                    source_b_tier=tier_b,
                    conflict_type="value_mismatch",
                    resolution=resolution,
                    resolution_notes=res_notes,
                ).to_dict())

    # Determine status
    if conflicts:
        has_unresolved = any(c["resolution"] == "unresolved" for c in conflicts)
        status = "conflicting"
        notes = (
            f"⚠ CONFLICT DETECTED: {len(conflicts)} conflicting source(s) found. "
            f"{'Manual verification required.' if has_unresolved else 'Higher-tier source preferred but conflict must be disclosed.'}"
        )
        confidence = CONFIDENCE_BY_TIER.get(primary_tier, 0.30) * 0.6  # Penalty for conflict
    elif len(sorted_records) >= 2:
        status = "verified"
        notes = f"Consistent across {len(sorted_records)} sources."
        confidence = min(CONFIDENCE_BY_TIER.get(primary_tier, 0.30) + 0.05, 0.99)
    else:
        status = "partial"
        notes = "Single source only. Cross-verification not possible."
        confidence = CONFIDENCE_BY_TIER.get(primary_tier, 0.30)

    return VerificationResult(
        field_name=field_name,
        status=status,
        primary_value=str(primary.get("value")),
        primary_source=primary.get("url"),
        primary_tier=primary_tier,
        confidence_score=round(confidence, 2),
        conflicts=conflicts,
        notes=notes,
    )


def verify_product(product: dict) -> dict:
    """
    Verify all fields in a product dict.
    product["evidence"] = {field_name: [list of source records]}
    """
    results = {}
    evidence = product.get("evidence", {})

    for field_name, source_records in evidence.items():
        results[field_name] = verify_field(field_name, source_records).to_dict()

    # Overall product status
    statuses = [r["status"] for r in results.values()]
    if "conflicting" in statuses:
        overall = "conflicting"
    elif all(s == "verified" for s in statuses):
        overall = "verified"
    elif any(s == "unverified" for s in statuses):
        overall = "partial"
    else:
        overall = "partial"

    conflict_count = sum(1 for s in statuses if s == "conflicting")
    avg_confidence = (
        sum(r["confidence_score"] for r in results.values()) / len(results)
        if results else 0.0
    )

    return {
        "product_id": product.get("product_id"),
        "institution": product.get("institution"),
        "overall_status": overall,
        "average_confidence": round(avg_confidence, 2),
        "conflict_count": conflict_count,
        "field_results": results,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="COMPARE AI Verification Engine")
    parser.add_argument("--products-file", help="JSON file with products to verify")
    parser.add_argument("--field", help="Single field to verify")
    parser.add_argument("--values", help='JSON array of values e.g. ["10%","11%"]')
    parser.add_argument("--sources", help='JSON array of source URLs')
    parser.add_argument("--source-types", help='JSON array of source types')
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    if args.products_file:
        products = json.loads(Path(args.products_file).read_text(encoding="utf-8"))
        if isinstance(products, list):
            results = [verify_product(p) for p in products]
        else:
            results = [verify_product(products)]

        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            for r in results:
                print(f"\n── Verification: {r['institution']} ──────────────────────")
                print(f"  Overall status:  {r['overall_status']}")
                print(f"  Avg confidence:  {r['average_confidence']:.0%}")
                print(f"  Conflicts:       {r['conflict_count']}")
                for field, fr in r["field_results"].items():
                    icon = "✓" if fr["status"] == "verified" else ("⚠" if fr["status"] == "conflicting" else "?")
                    print(f"  {icon} {field}: {fr['primary_value']} [{fr['status']}]")
                    if fr["conflicts"]:
                        for c in fr["conflicts"]:
                            print(f"      CONFLICT: {c['source_a_value']} vs {c['source_b_value']}")
                            print(f"      → {c['resolution_notes']}")

    elif args.field and args.values:
        values = json.loads(args.values)
        sources = json.loads(args.sources) if args.sources else ["" for _ in values]
        source_types = json.loads(args.source_types) if args.source_types else ["unknown" for _ in values]

        source_records = [
            {"url": s, "value": v, "source_type": t}
            for s, v, t in zip(sources, values, source_types)
        ]
        result = verify_field(args.field, source_records)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"\n── Field Verification: {args.field} ────────────────────────")
            print(f"  Status:     {result.status}")
            print(f"  Value:      {result.primary_value}")
            print(f"  Source:     Tier {result.primary_tier} — {result.primary_source}")
            print(f"  Confidence: {result.confidence_score:.0%}")
            print(f"  Notes:      {result.notes}")
            if result.conflicts:
                print(f"\n  ⚠ Conflicts ({len(result.conflicts)}):")
                for c in result.conflicts:
                    print(f"    {c['source_a_value']} (Tier {c['source_a_tier']}) vs {c['source_b_value']} (Tier {c['source_b_tier']})")
                    print(f"    → {c['resolution_notes']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    from pathlib import Path
    main()
