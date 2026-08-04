#!/usr/bin/env python3
"""
COMPARE AI — Deposit Calculator (Deterministic)

Calculates returns for: Savings, FDR, DPS, Term Deposits.

Formulas:
    Simple Interest:  return = P × (r/100) × (t/12)
    Compound:         A = P × (1 + r/n)^(n×t)  [only when compounding documented]
    DPS maturity:     monthly_installment × months + cumulative_interest

Usage:
    python3 deposit_calculator.py --principal 500000 --rate 7.5 --tenure 12 --type fdr
    python3 deposit_calculator.py --principal 5000 --rate 6.0 --tenure 36 --type dps
    python3 deposit_calculator.py --json --principal 500000 --rate 7.5 --tenure 12 --type savings
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, asdict
from typing import Optional


DEPOSIT_TYPES = ["savings", "fdr", "dps", "term_deposit", "recurring", "islamic_deposit"]


@dataclass
class DepositCalculationResult:
    # Inputs
    deposit_type: str
    principal: float
    annual_rate_pct: float
    tenure_months: int
    currency: str
    payout_frequency: str  # "at_maturity" | "monthly" | "quarterly" | "annually"
    compounding: str  # "none" | "monthly" | "quarterly" | "annually"

    # Results
    gross_return: float          # total interest/profit earned
    gross_maturity_value: float  # principal + gross_return
    withholding_tax: float       # if rate known
    net_return: float            # after tax (if rate known)
    net_maturity_value: float    # principal + net_return
    effective_annual_rate: float # EAR considering compounding

    # DPS specific
    monthly_installment: Optional[float]  # for DPS
    total_deposits: Optional[float]        # for DPS (monthly × months)

    # Labels
    rate_label: str   # "interest rate" or "profit rate" (Islamic)
    calculation_label: str
    disclaimer: str
    withholding_tax_status: str  # "applied" | "unknown" | "not_applicable"

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_simple_interest(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
) -> tuple[float, float]:
    """Returns (interest_earned, maturity_value)."""
    interest = principal * (annual_rate_pct / 100.0) * (tenure_months / 12.0)
    return round(interest, 2), round(principal + interest, 2)


def calculate_compound_interest(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    compounds_per_year: int = 4,
) -> tuple[float, float]:
    """Returns (interest_earned, maturity_value). Only use when compounding is documented."""
    r = annual_rate_pct / 100.0
    n = compounds_per_year
    t = tenure_months / 12.0
    maturity = principal * math.pow(1 + r / n, n * t)
    maturity = round(maturity, 2)
    interest = round(maturity - principal, 2)
    return interest, maturity


def calculate_effective_annual_rate(
    annual_rate_pct: float,
    compounds_per_year: int = 1,
) -> float:
    """EAR = (1 + r/n)^n - 1"""
    r = annual_rate_pct / 100.0
    n = compounds_per_year
    ear = math.pow(1 + r / n, n) - 1
    return round(ear * 100, 4)


def calculate_dps_maturity(
    monthly_installment: float,
    annual_rate_pct: float,
    tenure_months: int,
) -> tuple[float, float, float]:
    """
    DPS (Deposit Pension Scheme) maturity calculation.
    Approximates interest as simple interest on average balance.
    Returns (total_deposits, estimated_interest, estimated_maturity).
    """
    total_deposits = monthly_installment * tenure_months
    # Average balance = total_deposits / 2 (simplified approximation)
    # More accurate: sum of (installment × months_remaining × rate/12)
    accumulated_interest = 0.0
    monthly_rate = annual_rate_pct / 12.0 / 100.0
    for month in range(1, tenure_months + 1):
        # Each installment earns interest for (tenure - month) remaining months
        remaining_months = tenure_months - month
        accumulated_interest += monthly_installment * monthly_rate * remaining_months
    maturity = round(total_deposits + accumulated_interest, 2)
    return round(total_deposits, 2), round(accumulated_interest, 2), maturity


def calculate_deposit(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    deposit_type: str = "fdr",
    currency: str = "BDT",
    payout_frequency: str = "at_maturity",
    use_compound: bool = False,
    compounds_per_year: int = 1,
    withholding_tax_pct: Optional[float] = None,
    is_islamic: bool = False,
) -> DepositCalculationResult:
    """Full deposit return calculation."""

    rate_label = "profit rate" if is_islamic else "interest rate"
    monthly_installment = None
    total_deposits_dps = None

    if deposit_type == "dps":
        # For DPS, principal is the monthly installment
        total_deposits_dps, gross_return, gross_maturity_value = calculate_dps_maturity(
            monthly_installment=principal,
            annual_rate_pct=annual_rate_pct,
            tenure_months=tenure_months,
        )
        monthly_installment = principal
        effective_annual_rate = annual_rate_pct  # DPS uses stated rate
    elif use_compound:
        gross_return, gross_maturity_value = calculate_compound_interest(
            principal, annual_rate_pct, tenure_months, compounds_per_year
        )
        effective_annual_rate = calculate_effective_annual_rate(annual_rate_pct, compounds_per_year)
    else:
        gross_return, gross_maturity_value = calculate_simple_interest(
            principal, annual_rate_pct, tenure_months
        )
        effective_annual_rate = annual_rate_pct

    # Withholding tax
    if withholding_tax_pct is not None:
        tax = round(gross_return * withholding_tax_pct / 100.0, 2)
        net_return = round(gross_return - tax, 2)
        net_maturity_value = round(gross_maturity_value - tax, 2)
        wht_status = "applied"
    else:
        tax = 0.0
        net_return = gross_return
        net_maturity_value = gross_maturity_value
        wht_status = "unknown"

    return DepositCalculationResult(
        deposit_type=deposit_type,
        principal=principal,
        annual_rate_pct=annual_rate_pct,
        tenure_months=tenure_months,
        currency=currency,
        payout_frequency=payout_frequency,
        compounding="none" if not use_compound else f"every {12//compounds_per_year} months",
        gross_return=gross_return,
        gross_maturity_value=gross_maturity_value,
        withholding_tax=tax,
        net_return=net_return,
        net_maturity_value=net_maturity_value,
        effective_annual_rate=effective_annual_rate,
        monthly_installment=monthly_installment,
        total_deposits=total_deposits_dps,
        rate_label=rate_label,
        calculation_label=f"Calculated using stated annual {rate_label} of {annual_rate_pct}%",
        disclaimer=(
            "This calculation uses the institution's published rate with simple interest "
            "unless compounding is explicitly documented. It is NOT an official product quotation. "
            "Actual returns, tax deductions, and terms depend on the financial institution."
        ),
        withholding_tax_status=wht_status,
    )


def format_deposit_result(result: DepositCalculationResult, symbol: str = "৳") -> str:
    lines = [
        f"\n── Deposit Calculation ({result.deposit_type.upper()}) ──────────────────────",
    ]

    if result.deposit_type == "dps":
        lines += [
            f"  Monthly Installment:     {symbol}{result.monthly_installment:>15,.2f}",
            f"  Tenure:                  {result.tenure_months:>13} months",
            f"  Total Deposited:         {symbol}{result.total_deposits:>15,.2f}",
        ]
    else:
        lines += [
            f"  Principal:               {symbol}{result.principal:>15,.2f}",
            f"  Annual {result.rate_label.title():13}  {result.annual_rate_pct:>14.2f}%",
            f"  Tenure:                  {result.tenure_months:>13} months",
        ]

    lines += [
        f"",
        f"  Gross Return:            {symbol}{result.gross_return:>15,.2f}",
        f"  Gross Maturity Value:    {symbol}{result.gross_maturity_value:>15,.2f}",
    ]

    if result.withholding_tax_status == "applied":
        lines += [
            f"  Withholding Tax:        -{symbol}{result.withholding_tax:>15,.2f}",
            f"  Net Return:              {symbol}{result.net_return:>15,.2f}",
            f"  Net Maturity Value:      {symbol}{result.net_maturity_value:>15,.2f}",
        ]
    else:
        lines.append(f"  Withholding Tax:         Not applied (rate unknown — check with institution)")

    lines += [
        f"  Effective Annual Rate:   {result.effective_annual_rate:>14.4f}%",
        f"  Payout Frequency:        {result.payout_frequency}",
        f"",
        f"  ⚠  {result.calculation_label}",
        f"────────────────────────────────────────────────────────────",
    ]
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="COMPARE AI Deposit Calculator")
    parser.add_argument("--principal", "-p", type=float, required=True,
                        help="Deposit amount (for DPS: monthly installment)")
    parser.add_argument("--rate", "-r", type=float, required=True,
                        help="Annual interest/profit rate (%)")
    parser.add_argument("--tenure", "-n", type=int, required=True, help="Tenure in months")
    parser.add_argument("--type", "-t", default="fdr",
                        choices=DEPOSIT_TYPES, help="Deposit type")
    parser.add_argument("--currency", default="BDT")
    parser.add_argument("--symbol", default="৳")
    parser.add_argument("--compound", action="store_true", help="Use compound interest")
    parser.add_argument("--compounds-per-year", type=int, default=4,
                        help="Compounding periods per year (if --compound)")
    parser.add_argument("--wht", type=float, default=None,
                        help="Withholding tax rate (%)")
    parser.add_argument("--islamic", action="store_true", help="Islamic product (profit rate)")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--payout", default="at_maturity",
                        choices=["at_maturity", "monthly", "quarterly", "annually"])
    args = parser.parse_args()

    result = calculate_deposit(
        principal=args.principal,
        annual_rate_pct=args.rate,
        tenure_months=args.tenure,
        deposit_type=args.type,
        currency=args.currency,
        payout_frequency=args.payout,
        use_compound=args.compound,
        compounds_per_year=args.compounds_per_year,
        withholding_tax_pct=args.wht,
        is_islamic=args.islamic,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_deposit_result(result, symbol=args.symbol))


if __name__ == "__main__":
    main()
