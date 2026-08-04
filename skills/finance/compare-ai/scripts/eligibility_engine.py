#!/usr/bin/env python3
"""
COMPARE AI — Eligibility Engine

Classifies user eligibility for financial products based on
published eligibility criteria. Never guarantees approval.

Classifications:
    likely_eligible       — meets all stated criteria
    possibly_eligible     — meets most, some criteria unclear
    likely_not_eligible   — fails at least one clear requirement
    unknown               — criteria not available from source

Usage:
    python3 eligibility_engine.py --age 30 --income 80000 --employment salaried
    python3 eligibility_engine.py --products-file products.json --age 30 --income 80000
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class EligibilityCriteria:
    """Published eligibility criteria from a financial institution."""
    minimum_age: Optional[int] = None
    maximum_age: Optional[int] = None
    minimum_income_monthly: Optional[float] = None
    maximum_income_monthly: Optional[float] = None
    employment_types_allowed: Optional[list] = None    # ["salaried", "self_employed", ...]
    residency_required: Optional[str] = None           # "BD" | "citizen" | None
    existing_customer_required: Optional[bool] = None
    collateral_required: Optional[bool] = None
    guarantor_required: Optional[bool] = None
    minimum_business_years: Optional[int] = None       # for SME/business loans
    minimum_loan_amount: Optional[float] = None
    maximum_loan_amount: Optional[float] = None
    source_url: Optional[str] = None
    source_checked_at: Optional[str] = None
    criteria_source_status: str = "unknown"            # "verified" | "partial" | "unknown"


@dataclass
class EligibilityResult:
    product_id: str
    institution: str
    product_name: str
    classification: str           # likely_eligible | possibly_eligible | likely_not_eligible | unknown
    score: float                  # 0.0 to 1.0
    passed_criteria: list
    failed_criteria: list
    unknown_criteria: list
    notes: str
    disclaimer: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UserProfile:
    age: Optional[int] = None
    monthly_income: Optional[float] = None
    employment_type: Optional[str] = None        # salaried | self_employed | professional | retired
    country_code: Optional[str] = None
    is_existing_customer: Optional[bool] = None
    has_collateral: Optional[bool] = None
    has_guarantor: Optional[bool] = None
    business_years: Optional[int] = None
    requested_amount: Optional[float] = None


EMPLOYMENT_EQUIVALENTS = {
    "salaried": ["salaried", "employed", "service_holder", "government", "private", "ngo"],
    "self_employed": ["self_employed", "business_owner", "entrepreneur", "proprietor"],
    "professional": ["professional", "doctor", "lawyer", "engineer", "architect", "accountant"],
    "retired": ["retired", "pensioner"],
    "farmer": ["farmer", "agriculture"],
}


def employment_matches(user_emp: str, allowed: list) -> bool:
    """Check if user's employment type matches allowed types."""
    if not user_emp or not allowed:
        return False
    user_lower = user_emp.lower()
    # Expand to equivalents
    for canon, variants in EMPLOYMENT_EQUIVALENTS.items():
        if user_lower in variants:
            user_lower = canon
            break
    return any(
        user_lower == a.lower() or user_lower in EMPLOYMENT_EQUIVALENTS.get(a.lower(), [])
        for a in allowed
    )


def evaluate_eligibility(
    product_id: str,
    institution: str,
    product_name: str,
    criteria: EligibilityCriteria,
    user: UserProfile,
) -> EligibilityResult:
    """
    Evaluate user eligibility against published product criteria.
    Returns classification and reasoning.
    """
    passed = []
    failed = []
    unknown = []

    # Age check
    if criteria.minimum_age is not None and user.age is not None:
        if user.age >= criteria.minimum_age:
            passed.append(f"Age {user.age} ≥ minimum {criteria.minimum_age}")
        else:
            failed.append(f"Age {user.age} < minimum required {criteria.minimum_age}")
    elif criteria.minimum_age is not None and user.age is None:
        unknown.append(f"Age requirement: minimum {criteria.minimum_age} (age not provided)")
    elif user.age is not None and criteria.minimum_age is None:
        unknown.append("Minimum age: not specified in published criteria")

    if criteria.maximum_age is not None and user.age is not None:
        if user.age <= criteria.maximum_age:
            passed.append(f"Age {user.age} ≤ maximum {criteria.maximum_age}")
        else:
            failed.append(f"Age {user.age} > maximum allowed {criteria.maximum_age}")

    # Income check
    if criteria.minimum_income_monthly is not None and user.monthly_income is not None:
        if user.monthly_income >= criteria.minimum_income_monthly:
            passed.append(f"Monthly income {user.monthly_income:,.0f} ≥ minimum {criteria.minimum_income_monthly:,.0f}")
        else:
            failed.append(f"Monthly income {user.monthly_income:,.0f} < minimum required {criteria.minimum_income_monthly:,.0f}")
    elif criteria.minimum_income_monthly is not None and user.monthly_income is None:
        unknown.append(f"Income requirement: minimum {criteria.minimum_income_monthly:,.0f}/month (income not provided)")

    # Employment check
    if criteria.employment_types_allowed is not None and user.employment_type is not None:
        if employment_matches(user.employment_type, criteria.employment_types_allowed):
            passed.append(f"Employment type '{user.employment_type}' is accepted")
        else:
            failed.append(f"Employment type '{user.employment_type}' not in allowed: {criteria.employment_types_allowed}")
    elif criteria.employment_types_allowed is not None and user.employment_type is None:
        unknown.append(f"Employment requirement: {criteria.employment_types_allowed} (not provided)")

    # Collateral
    if criteria.collateral_required is True and user.has_collateral is not None:
        if user.has_collateral:
            passed.append("Collateral available — requirement met")
        else:
            failed.append("Collateral required but not available")
    elif criteria.collateral_required is True and user.has_collateral is None:
        unknown.append("Collateral required — availability not specified")
    elif criteria.collateral_required is False:
        passed.append("No collateral required")
    elif criteria.collateral_required is None:
        unknown.append("Collateral requirement: not specified in published criteria")

    # Loan amount
    if criteria.minimum_loan_amount is not None and user.requested_amount is not None:
        if user.requested_amount >= criteria.minimum_loan_amount:
            passed.append(f"Requested amount {user.requested_amount:,.0f} ≥ minimum {criteria.minimum_loan_amount:,.0f}")
        else:
            failed.append(f"Requested amount {user.requested_amount:,.0f} < minimum {criteria.minimum_loan_amount:,.0f}")

    if criteria.maximum_loan_amount is not None and user.requested_amount is not None:
        if user.requested_amount <= criteria.maximum_loan_amount:
            passed.append(f"Requested amount {user.requested_amount:,.0f} ≤ maximum {criteria.maximum_loan_amount:,.0f}")
        else:
            failed.append(f"Requested amount {user.requested_amount:,.0f} > maximum {criteria.maximum_loan_amount:,.0f}")

    # Existing customer
    if criteria.existing_customer_required is True and user.is_existing_customer is not None:
        if user.is_existing_customer:
            passed.append("Existing customer requirement met")
        else:
            failed.append("Existing customer required but user is not a current customer")
    elif criteria.existing_customer_required is True and user.is_existing_customer is None:
        unknown.append("Existing customer may be required — not confirmed")

    # Classify
    total = len(passed) + len(failed) + len(unknown)
    if total == 0:
        classification = "unknown"
        score = 0.0
        notes = "No eligibility criteria available from official sources."
    elif failed:
        classification = "likely_not_eligible"
        score = max(0.0, len(passed) / total - 0.3)
        notes = f"Fails {len(failed)} published requirement(s). Final decision rests with the institution."
    elif unknown and not failed:
        if len(passed) >= len(unknown):
            classification = "possibly_eligible"
            score = 0.6 + (len(passed) / total * 0.3)
            notes = f"Meets {len(passed)} criteria but {len(unknown)} requirement(s) could not be verified."
        else:
            classification = "unknown"
            score = 0.4
            notes = f"Insufficient eligibility information from published sources."
    else:
        classification = "likely_eligible"
        score = min(0.95, 0.7 + len(passed) / total * 0.3)
        notes = f"Meets all {len(passed)} stated eligibility criteria."

    return EligibilityResult(
        product_id=product_id,
        institution=institution,
        product_name=product_name,
        classification=classification,
        score=round(score, 2),
        passed_criteria=passed,
        failed_criteria=failed,
        unknown_criteria=unknown,
        notes=notes,
        disclaimer=(
            "This eligibility assessment is based on published criteria only. "
            "COMPARE AI does not guarantee loan approval. "
            "Final eligibility and approval decisions rest entirely with the financial institution."
        ),
    )


def format_result(result: EligibilityResult) -> str:
    icons = {
        "likely_eligible": "✓",
        "possibly_eligible": "~",
        "likely_not_eligible": "✗",
        "unknown": "?",
    }
    icon = icons.get(result.classification, "?")
    lines = [
        f"\n── Eligibility: {result.institution} — {result.product_name} ───────",
        f"  {icon} Classification:  {result.classification}",
        f"  Score:            {result.score:.0%}",
    ]
    if result.passed_criteria:
        lines.append(f"\n  ✓ Passed ({len(result.passed_criteria)}):")
        for c in result.passed_criteria:
            lines.append(f"    + {c}")
    if result.failed_criteria:
        lines.append(f"\n  ✗ Failed ({len(result.failed_criteria)}):")
        for c in result.failed_criteria:
            lines.append(f"    - {c}")
    if result.unknown_criteria:
        lines.append(f"\n  ? Unknown ({len(result.unknown_criteria)}):")
        for c in result.unknown_criteria:
            lines.append(f"    ? {c}")
    lines += [f"\n  Note: {result.notes}", f"  ⚠  {result.disclaimer}"]
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="COMPARE AI Eligibility Engine")
    parser.add_argument("--age", type=int)
    parser.add_argument("--income", type=float, help="Monthly income")
    parser.add_argument("--employment", default=None,
                        choices=["salaried", "self_employed", "professional", "retired", "farmer"])
    parser.add_argument("--collateral", type=str, choices=["yes", "no"])
    parser.add_argument("--amount", type=float, help="Requested loan/deposit amount")
    parser.add_argument("--existing-customer", type=str, choices=["yes", "no"])
    # Criteria (for testing)
    parser.add_argument("--min-age", type=int, default=None)
    parser.add_argument("--max-age", type=int, default=None)
    parser.add_argument("--min-income", type=float, default=None)
    parser.add_argument("--collateral-required", type=str, choices=["yes", "no", "unknown"])
    parser.add_argument("--min-amount", type=float, default=None)
    parser.add_argument("--max-amount", type=float, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    user = UserProfile(
        age=args.age,
        monthly_income=args.income,
        employment_type=args.employment,
        has_collateral=True if args.collateral == "yes" else (False if args.collateral == "no" else None),
        requested_amount=args.amount,
        is_existing_customer=True if args.existing_customer == "yes" else (
            False if args.existing_customer == "no" else None
        ),
    )

    criteria = EligibilityCriteria(
        minimum_age=args.min_age,
        maximum_age=args.max_age,
        minimum_income_monthly=args.min_income,
        collateral_required=(
            True if args.collateral_required == "yes"
            else (False if args.collateral_required == "no" else None)
        ),
        minimum_loan_amount=args.min_amount,
        maximum_loan_amount=args.max_amount,
    )

    result = evaluate_eligibility(
        product_id="test",
        institution="Test Institution",
        product_name="Personal Loan",
        criteria=criteria,
        user=user,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_result(result))


if __name__ == "__main__":
    main()
