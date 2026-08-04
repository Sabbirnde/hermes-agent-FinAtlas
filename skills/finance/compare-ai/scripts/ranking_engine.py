#!/usr/bin/env python3
"""
COMPARE AI — Ranking Engine

Transparent, priority-weighted product ranking.
Explains why each product ranks where it does.

Usage:
    python3 ranking_engine.py --products-file products.json --priority lowest_total_cost --top 5
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Optional


# ── Priority Configurations ───────────────────────────────────────────────────

PRIORITY_WEIGHTS = {
    "lowest_total_cost": {
        "financial_cost_return": 0.40,
        "eligibility_fit": 0.20,
        "fees": 0.15,
        "flexibility": 0.10,
        "constraints": 0.10,
        "source_confidence": 0.05,
    },
    "lowest_monthly_payment": {
        "financial_cost_return": 0.45,
        "eligibility_fit": 0.20,
        "fees": 0.10,
        "flexibility": 0.10,
        "constraints": 0.10,
        "source_confidence": 0.05,
    },
    "highest_return": {
        "financial_cost_return": 0.50,
        "eligibility_fit": 0.10,
        "fees": 0.10,
        "flexibility": 0.20,
        "constraints": 0.05,
        "source_confidence": 0.05,
    },
    "best_eligibility": {
        "financial_cost_return": 0.20,
        "eligibility_fit": 0.40,
        "fees": 0.10,
        "flexibility": 0.15,
        "constraints": 0.10,
        "source_confidence": 0.05,
    },
    "no_collateral": {
        "financial_cost_return": 0.25,
        "eligibility_fit": 0.35,
        "fees": 0.10,
        "flexibility": 0.15,
        "constraints": 0.10,
        "source_confidence": 0.05,
    },
    "lowest_fees": {
        "financial_cost_return": 0.25,
        "eligibility_fit": 0.15,
        "fees": 0.40,
        "flexibility": 0.10,
        "constraints": 0.05,
        "source_confidence": 0.05,
    },
    "maximum_flexibility": {
        "financial_cost_return": 0.20,
        "eligibility_fit": 0.15,
        "fees": 0.10,
        "flexibility": 0.40,
        "constraints": 0.10,
        "source_confidence": 0.05,
    },
}

DEFAULT_PRIORITY = "lowest_total_cost"


@dataclass
class RankedProduct:
    rank: int
    product_id: str
    institution: str
    product_name: str
    country_code: str

    # Financial scores
    rate: Optional[float]
    rate_display: str
    monthly_installment: Optional[float]
    total_cost: Optional[float]
    return_amount: Optional[float]
    known_fees: Optional[float]

    # Ranking
    composite_score: float
    component_scores: dict
    weights_used: dict
    priority: str
    why_it_ranks: str   # Plain English explanation

    # Verification
    verification_status: str
    confidence: float
    source_url: Optional[str]
    checked_at: Optional[str]

    # Eligibility
    eligibility_classification: Optional[str]
    eligibility_score: float

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_to_score(
    value: Optional[float],
    all_values: list[Optional[float]],
    higher_is_better: bool = False,
) -> float:
    """
    Normalize a value to 0–1 range across all products.
    lower_is_better (default): lowest value → score 1.0, highest → score 0.0
    higher_is_better: highest value → score 1.0, lowest → score 0.0
    """
    valid = [v for v in all_values if v is not None]
    if not valid or value is None:
        return 0.5  # neutral score for unknown

    min_v = min(valid)
    max_v = max(valid)

    if max_v == min_v:
        return 1.0  # all same — full score

    normalized = (value - min_v) / (max_v - min_v)
    return normalized if higher_is_better else (1.0 - normalized)


def score_flexibility(product: dict) -> float:
    """Score product on flexibility (premature withdrawal, prepayment, etc.)."""
    score = 0.5  # default
    flags = []

    # Loan flexibility
    if product.get("prepayment_allowed") is True:
        flags.append(0.3)
    if product.get("prepayment_fee") == 0:
        flags.append(0.2)

    # Deposit flexibility
    if product.get("premature_withdrawal_allowed") is True:
        flags.append(0.3)
    if product.get("lock_in_months") is not None:
        lock = product["lock_in_months"]
        if lock == 0:
            flags.append(0.2)
        elif lock <= 3:
            flags.append(0.1)

    if flags:
        score = min(1.0, 0.3 + sum(flags))
    return score


def score_constraints(product: dict, user_amount: Optional[float], user_tenure: Optional[int]) -> float:
    """Score how well product constraints match user needs."""
    score = 0.8  # default (assume compatible unless proven otherwise)

    if user_amount is not None:
        min_amt = product.get("minimum_loan_amount") or product.get("minimum_deposit")
        max_amt = product.get("maximum_loan_amount") or product.get("maximum_deposit")
        if min_amt and user_amount < min_amt:
            score -= 0.4
        if max_amt and user_amount > max_amt:
            score -= 0.4

    if user_tenure is not None:
        min_ten = product.get("minimum_tenure_months")
        max_ten = product.get("maximum_tenure_months")
        if min_ten and user_tenure < min_ten:
            score -= 0.3
        if max_ten and user_tenure > max_ten:
            score -= 0.3

    return max(0.0, score)


def build_why_it_ranks(product: dict, rank: int, priority: str, component_scores: dict) -> str:
    """Generate plain English explanation for ranking."""
    institution = product.get("institution", "This institution")
    rate = product.get("rate")
    total_cost = product.get("estimated_total_cost")
    monthly = product.get("monthly_installment")
    ret = product.get("estimated_return")

    lines = []

    if priority == "lowest_total_cost" and total_cost:
        lines.append(f"Lowest estimated total cost among verified products (৳{total_cost:,.0f}).")
    elif priority == "lowest_monthly_payment" and monthly:
        lines.append(f"Lowest estimated monthly payment (৳{monthly:,.0f}).")
    elif priority == "highest_return" and ret:
        lines.append(f"Highest estimated return (৳{ret:,.0f}).")
    elif priority in ("best_eligibility", "no_collateral"):
        elig = product.get("eligibility_classification", "unknown")
        lines.append(f"Eligibility classification: {elig}.")
        if product.get("collateral_required") is False:
            lines.append("No collateral required.")

    if product.get("verification_status") == "verified":
        lines.append("Rate verified from official source.")
    if product.get("confidence", 0) >= 0.90:
        lines.append(f"High source confidence ({product['confidence']:.0%}).")

    if rank == 1:
        lines.insert(0, f"Top match based on {priority.replace('_', ' ')}. ")

    return " ".join(lines) if lines else f"Ranked by {priority.replace('_', ' ')}."


def rank_products(
    products: list[dict],
    priority: str = "lowest_total_cost",
    user_amount: Optional[float] = None,
    user_tenure: Optional[int] = None,
    top_n: int = 5,
) -> list[RankedProduct]:
    """
    Rank products using transparent weighted scoring.
    Returns top N ranked products with explanations.
    """
    weights = PRIORITY_WEIGHTS.get(priority, PRIORITY_WEIGHTS[DEFAULT_PRIORITY])

    # Extract all values for normalization
    all_total_costs = [p.get("estimated_total_cost") for p in products]
    all_monthly = [p.get("monthly_installment") for p in products]
    all_rates = [p.get("rate") for p in products]
    all_returns = [p.get("estimated_return") for p in products]
    all_fees = [p.get("known_fees_total", 0) for p in products]
    all_elig_scores = [p.get("eligibility_score", 0.5) for p in products]
    all_confidence = [p.get("confidence", 0.5) for p in products]

    scored = []
    for product in products:
        # Financial score
        if priority in ("highest_return",):
            financial_score = normalize_to_score(
                product.get("estimated_return"), all_returns, higher_is_better=True
            )
        elif priority == "lowest_monthly_payment":
            financial_score = normalize_to_score(
                product.get("monthly_installment"), all_monthly, higher_is_better=False
            )
        else:
            financial_score = normalize_to_score(
                product.get("estimated_total_cost"), all_total_costs, higher_is_better=False
            )

        # Eligibility score
        elig_score = product.get("eligibility_score", 0.5)
        elig_bonus = 0.3 if priority == "no_collateral" and product.get("collateral_required") is False else 0.0
        elig_combined = min(1.0, elig_score + elig_bonus)

        # Fees score
        fees_score = normalize_to_score(
            product.get("known_fees_total", 0), all_fees, higher_is_better=False
        )

        # Flexibility
        flex_score = score_flexibility(product)

        # Constraints
        constraint_score = score_constraints(product, user_amount, user_tenure)

        # Source confidence
        confidence_score = normalize_to_score(
            product.get("confidence", 0.5), all_confidence, higher_is_better=True
        )

        component_scores = {
            "financial_cost_return": round(financial_score, 3),
            "eligibility_fit": round(elig_combined, 3),
            "fees": round(fees_score, 3),
            "flexibility": round(flex_score, 3),
            "constraints": round(constraint_score, 3),
            "source_confidence": round(confidence_score, 3),
        }

        composite = sum(component_scores[k] * weights[k] for k in weights)

        scored.append((round(composite, 4), product, component_scores))

    # Sort descending by composite score
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for rank, (composite, product, component_scores) in enumerate(scored[:top_n], 1):
        why = build_why_it_ranks(product, rank, priority, component_scores)
        results.append(RankedProduct(
            rank=rank,
            product_id=product.get("product_id", ""),
            institution=product.get("institution", ""),
            product_name=product.get("product_name", ""),
            country_code=product.get("country_code", "BD"),
            rate=product.get("rate"),
            rate_display=product.get("rate_display", "Unknown"),
            monthly_installment=product.get("monthly_installment"),
            total_cost=product.get("estimated_total_cost"),
            return_amount=product.get("estimated_return"),
            known_fees=product.get("known_fees_total"),
            composite_score=composite,
            component_scores=component_scores,
            weights_used=weights,
            priority=priority,
            why_it_ranks=why,
            verification_status=product.get("verification_status", "unknown"),
            confidence=product.get("confidence", 0.0),
            source_url=product.get("source_url"),
            checked_at=product.get("checked_at"),
            eligibility_classification=product.get("eligibility_classification"),
            eligibility_score=product.get("eligibility_score", 0.5),
        ))

    return results


def format_ranking(results: list[RankedProduct], symbol: str = "৳") -> str:
    lines = [f"\n── Ranked Results (Priority: {results[0].priority if results else 'N/A'}) ──────"]
    for r in results:
        lines += [
            f"\n{'🥇' if r.rank == 1 else '🥈' if r.rank == 2 else '🥉' if r.rank == 3 else f'#{r.rank}'}  {r.institution} — {r.product_name}",
            f"   Rate:         {r.rate_display}",
        ]
        if r.monthly_installment:
            lines.append(f"   Monthly:      {symbol}{r.monthly_installment:,.2f}")
        if r.total_cost:
            lines.append(f"   Total cost:   {symbol}{r.total_cost:,.2f}")
        if r.return_amount:
            lines.append(f"   Est. return:  {symbol}{r.return_amount:,.2f}")
        lines += [
            f"   Score:        {r.composite_score:.2%}",
            f"   Why:          {r.why_it_ranks}",
            f"   Verified:     {r.verification_status} ({r.confidence:.0%} confidence)",
        ]
        if r.checked_at:
            lines.append(f"   Checked:      {r.checked_at}")
    return "\n".join(lines)


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="COMPARE AI Ranking Engine")
    parser.add_argument("--products-file", required=True, help="JSON file with products")
    parser.add_argument("--priority", default="lowest_total_cost",
                        choices=list(PRIORITY_WEIGHTS.keys()))
    parser.add_argument("--top", type=int, default=5, help="Number of results")
    parser.add_argument("--amount", type=float, help="User requested amount")
    parser.add_argument("--tenure", type=int, help="User requested tenure (months)")
    parser.add_argument("--symbol", default="৳")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from pathlib import Path
    products = json.loads(Path(args.products_file).read_text(encoding="utf-8"))
    if not isinstance(products, list):
        products = [products]

    results = rank_products(products, args.priority, args.amount, args.tenure, args.top)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False))
    else:
        print(format_ranking(results, symbol=args.symbol))


if __name__ == "__main__":
    main()
