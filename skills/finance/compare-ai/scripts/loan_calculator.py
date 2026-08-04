#!/usr/bin/env python3
"""
COMPARE AI — Loan Calculator (Deterministic)

NEVER use an LLM for financial calculations. This script uses standard formulas.

EMI Formula (Standard Amortizing Loan):
    EMI = P × r × (1+r)^N / ((1+r)^N - 1)
    where:
        P = principal
        r = monthly interest rate = annual_rate / 12 / 100
        N = tenure in months

Usage:
    python3 loan_calculator.py --principal 500000 --rate 12.0 --tenure 60
    python3 loan_calculator.py --principal 500000 --rate 12.0 --tenure 60 --fees 5000 --fee-pct 1.0
    python3 loan_calculator.py --json --principal 500000 --rate 12.0 --tenure 60
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class LoanCalculationResult:
    # Inputs
    principal: float
    annual_rate_pct: float
    tenure_months: int
    currency: str

    # Core calculation
    monthly_rate: float
    monthly_installment: float
    total_payment: float
    total_interest: float

    # Fees
    processing_fee_flat: float
    processing_fee_pct_amount: float
    documentation_fee: float
    other_fees: float
    total_known_fees: float

    # Summary
    estimated_total_cost: float

    # Labels — always shown to user
    calculation_label: str
    disclaimer: str

    # Status
    rate_type: str  # "unknown" | "fixed" | "variable"
    confidence: str  # "calculated" | "estimated"

    def to_dict(self) -> dict:
        return asdict(self)

    def format_currency(self, amount: float, symbol: str = "৳") -> str:
        return f"{symbol}{amount:,.2f}"


def calculate_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """
    Standard EMI formula for amortizing loans.
    Returns exact monthly installment.
    """
    if annual_rate_pct <= 0:
        # Zero-interest loan: equal principal payments
        return round(principal / tenure_months, 2)

    r = annual_rate_pct / 12.0 / 100.0  # Monthly interest rate
    n = tenure_months

    # EMI = P × r × (1+r)^N / ((1+r)^N - 1)
    compound = math.pow(1 + r, n)
    emi = principal * r * compound / (compound - 1)
    return round(emi, 2)


def calculate_loan(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    currency: str = "BDT",
    processing_fee_flat: float = 0.0,
    processing_fee_pct: float = 0.0,
    documentation_fee: float = 0.0,
    other_fees: float = 0.0,
    rate_type: str = "unknown",
) -> LoanCalculationResult:
    """
    Full loan cost calculation.
    All amounts are in the specified currency.
    """
    r = annual_rate_pct / 12.0 / 100.0
    n = tenure_months

    # EMI
    emi = calculate_emi(principal, annual_rate_pct, tenure_months)

    # Totals
    total_payment = round(emi * tenure_months, 2)
    total_interest = round(total_payment - principal, 2)

    # Fees
    processing_fee_pct_amount = round(principal * processing_fee_pct / 100.0, 2)
    total_known_fees = round(
        processing_fee_flat + processing_fee_pct_amount + documentation_fee + other_fees, 2
    )

    # Estimated total cost = total repayment + upfront fees
    estimated_total_cost = round(total_payment + total_known_fees, 2)

    return LoanCalculationResult(
        principal=principal,
        annual_rate_pct=annual_rate_pct,
        tenure_months=tenure_months,
        currency=currency,
        monthly_rate=round(r * 100, 6),
        monthly_installment=emi,
        total_payment=total_payment,
        total_interest=total_interest,
        processing_fee_flat=processing_fee_flat,
        processing_fee_pct_amount=processing_fee_pct_amount,
        documentation_fee=documentation_fee,
        other_fees=other_fees,
        total_known_fees=total_known_fees,
        estimated_total_cost=estimated_total_cost,
        rate_type=rate_type,
        calculation_label="Calculated from published annual interest rate",
        disclaimer=(
            "This EMI is calculated using the standard amortizing loan formula "
            "from the institution's published rate. It is NOT an official loan quotation. "
            "Actual EMI, total cost, and approval depend on the financial institution."
        ),
        confidence="calculated",
    )


def format_loan_result(result: LoanCalculationResult, symbol: str = "৳") -> str:
    """Format calculation result for human-readable display."""
    lines = [
        f"\n── Loan Calculation ─────────────────────────────────────",
        f"  Principal:               {symbol}{result.principal:>15,.2f}",
        f"  Annual Interest Rate:    {result.annual_rate_pct:>14.2f}%",
        f"  Monthly Rate:            {result.monthly_rate:>14.4f}%",
        f"  Tenure:                  {result.tenure_months:>13} months",
        f"",
        f"  Monthly Installment:     {symbol}{result.monthly_installment:>15,.2f}",
        f"  Total Payments:          {symbol}{result.total_payment:>15,.2f}",
        f"  Total Interest:          {symbol}{result.total_interest:>15,.2f}",
    ]

    if result.total_known_fees > 0:
        lines += [
            f"",
            f"  Known Fees:",
            f"    Processing (flat):   {symbol}{result.processing_fee_flat:>15,.2f}" if result.processing_fee_flat else "",
            f"    Processing (% of P): {symbol}{result.processing_fee_pct_amount:>15,.2f}" if result.processing_fee_pct_amount else "",
            f"    Documentation:       {symbol}{result.documentation_fee:>15,.2f}" if result.documentation_fee else "",
            f"    Other:               {symbol}{result.other_fees:>15,.2f}" if result.other_fees else "",
            f"    Total Known Fees:    {symbol}{result.total_known_fees:>15,.2f}",
        ]

    lines += [
        f"",
        f"  Est. Total Cost:         {symbol}{result.estimated_total_cost:>15,.2f}",
        f"  (principal + interest + known fees)",
        f"",
        f"  ⚠  {result.calculation_label}",
        f"──────────────────────────────────────────────────────────",
    ]

    return "\n".join(l for l in lines if l is not None)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="COMPARE AI Loan Calculator")
    parser.add_argument("--principal", "-p", type=float, required=True, help="Loan principal")
    parser.add_argument("--rate", "-r", type=float, required=True, help="Annual interest rate (%)")
    parser.add_argument("--tenure", "-n", type=int, required=True, help="Tenure in months")
    parser.add_argument("--currency", default="BDT", help="Currency code")
    parser.add_argument("--symbol", default="৳", help="Currency symbol")
    parser.add_argument("--fees", type=float, default=0.0, help="Processing fee (flat amount)")
    parser.add_argument("--fee-pct", type=float, default=0.0, help="Processing fee (% of principal)")
    parser.add_argument("--doc-fee", type=float, default=0.0, help="Documentation fee")
    parser.add_argument("--other-fees", type=float, default=0.0, help="Other known fees")
    parser.add_argument("--rate-type", default="unknown", choices=["fixed", "variable", "unknown"])
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    result = calculate_loan(
        principal=args.principal,
        annual_rate_pct=args.rate,
        tenure_months=args.tenure,
        currency=args.currency,
        processing_fee_flat=args.fees,
        processing_fee_pct=args.fee_pct,
        documentation_fee=args.doc_fee,
        other_fees=args.other_fees,
        rate_type=args.rate_type,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_loan_result(result, symbol=args.symbol))


if __name__ == "__main__":
    main()
