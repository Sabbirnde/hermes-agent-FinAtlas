#!/usr/bin/env python3
"""
COMPARE AI — Intent Agent
Converts natural language financial queries into structured JSON intent.

Usage:
    python3 intent_agent.py "I need a 5 lakh personal loan for 5 years"
    python3 intent_agent.py --query "Best FDR rate for 1 year" --country BD
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Country Registry ──────────────────────────────────────────────────────────

COUNTRY_REGISTRY = {
    "BD": {"name": "Bangladesh", "currency": "BDT", "symbol": "৳"},
    "IN": {"name": "India", "currency": "INR", "symbol": "₹"},
    "PK": {"name": "Pakistan", "currency": "PKR", "symbol": "Rs"},
    "NG": {"name": "Nigeria", "currency": "NGN", "symbol": "₦"},
    "MY": {"name": "Malaysia", "currency": "MYR", "symbol": "RM"},
    "ID": {"name": "Indonesia", "currency": "IDR", "symbol": "Rp"},
    "PH": {"name": "Philippines", "currency": "PHP", "symbol": "₱"},
    "NP": {"name": "Nepal", "currency": "NPR", "symbol": "Rs"},
    "LK": {"name": "Sri Lanka", "currency": "LKR", "symbol": "Rs"},
    "SA": {"name": "Saudi Arabia", "currency": "SAR", "symbol": "﷼"},
    "AE": {"name": "UAE", "currency": "AED", "symbol": "د.إ"},
    "EG": {"name": "Egypt", "currency": "EGP", "symbol": "£E"},
    "ZA": {"name": "South Africa", "currency": "ZAR", "symbol": "R"},
    "GH": {"name": "Ghana", "currency": "GHS", "symbol": "₵"},
    "TZ": {"name": "Tanzania", "currency": "TZS", "symbol": "TSh"},
}

# ── Product Taxonomy ──────────────────────────────────────────────────────────

PRODUCT_KEYWORDS = {
    "personal_loan": ["personal loan", "consumer loan", "personal finance", "individual loan"],
    "home_loan": ["home loan", "mortgage", "housing loan", "home finance", "property loan"],
    "auto_loan": ["auto loan", "car loan", "vehicle loan", "automobile loan"],
    "sme_loan": ["sme loan", "sme finance", "small business loan", "business loan", "enterprise loan"],
    "education_loan": ["education loan", "student loan", "study loan", "educational finance"],
    "agriculture_loan": ["agriculture loan", "farm loan", "agricultural credit", "crop loan"],
    "microfinance_loan": ["microfinance", "micro loan", "micro credit", "microcredit"],
    "savings": ["savings account", "savings", "bank account", "current account"],
    "fdr": ["fdr", "fixed deposit", "term deposit", "fixed deposit receipt", "time deposit"],
    "dps": ["dps", "deposit pension", "monthly savings scheme", "recurring deposit"],
    "insurance": ["insurance", "life insurance", "health insurance"],
    "bond": ["bond", "sanchaypatra", "savings certificate", "government bond"],
}

PRIORITY_KEYWORDS = {
    "lowest_total_cost": ["cheapest", "lowest cost", "least expensive", "minimum cost", "cheapest option", "best deal"],
    "lowest_monthly_payment": ["lowest emi", "lowest monthly", "minimum installment", "smallest payment"],
    "highest_return": ["highest return", "best return", "maximum return", "highest rate", "best rate", "highest interest"],
    "best_eligibility": ["easy to get", "easy approval", "no collateral", "quick approval", "easy eligibility"],
    "no_collateral": ["no collateral", "without collateral", "unsecured", "no security"],
    "lowest_fees": ["lowest fees", "no fees", "minimum fees", "zero processing fee"],
    "maximum_flexibility": ["flexible", "most flexible", "early repayment", "prepayment allowed"],
}

EMPLOYMENT_KEYWORDS = {
    "salaried": ["salaried", "employed", "job", "service holder", "government employee", "private employee"],
    "self_employed": ["self employed", "business owner", "entrepreneur", "freelancer", "self-employed"],
    "professional": ["doctor", "lawyer", "engineer", "architect", "accountant", "consultant"],
}


# ── Amount Extraction ─────────────────────────────────────────────────────────

def extract_amount(text: str) -> Optional[float]:
    """Extract monetary amount from natural language."""
    text_lower = text.lower()

    # Bengali/South Asian number words
    lakh_match = re.search(r'([\d,.]+)\s*(?:lakh|lac|লাখ)', text_lower)
    if lakh_match:
        return float(lakh_match.group(1).replace(',', '')) * 100_000

    crore_match = re.search(r'([\d,.]+)\s*(?:crore|কোটি)', text_lower)
    if crore_match:
        return float(crore_match.group(1).replace(',', '')) * 10_000_000

    thousand_match = re.search(r'([\d,.]+)\s*(?:thousand|হাজার|k\b)', text_lower)
    if thousand_match:
        return float(thousand_match.group(1).replace(',', '')) * 1_000

    million_match = re.search(r'([\d,.]+)\s*(?:million|m\b)', text_lower)
    if million_match:
        return float(million_match.group(1).replace(',', '')) * 1_000_000

    # Currency symbol with number: ৳500,000 or ৳5,00,000 (Indian grouping)
    currency_match = re.search(r'[৳₹₦₱﷼$€£][\s]?([\d,]+)', text)
    if currency_match:
        return float(currency_match.group(1).replace(',', ''))

    # Plain number (at least 4 digits, likely an amount)
    plain_match = re.search(r'\b(\d{4,})\b', text)
    if plain_match:
        return float(plain_match.group(1))

    return None


def extract_tenure(text: str) -> Optional[int]:
    """Extract tenure in months from natural language."""
    text_lower = text.lower()

    # Years
    year_match = re.search(r'(\d+)\s*(?:year|yr|বছর)', text_lower)
    if year_match:
        return int(year_match.group(1)) * 12

    # Months
    month_match = re.search(r'(\d+)\s*(?:month|মাস)', text_lower)
    if month_match:
        return int(month_match.group(1))

    return None


def extract_product_type(text: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (category, subcategory) from query text."""
    text_lower = text.lower()

    for subcategory, keywords in PRODUCT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                if subcategory in ("personal_loan", "home_loan", "auto_loan",
                                   "sme_loan", "education_loan", "agriculture_loan",
                                   "microfinance_loan"):
                    return "loan", subcategory
                elif subcategory in ("savings", "fdr", "dps", "bond"):
                    return "deposit", subcategory
                elif subcategory == "insurance":
                    return "insurance", subcategory

    # Generic loan detection
    if re.search(r'\bloan\b|\bfinance\b|\bcredit\b|\bborrow\b', text_lower):
        return "loan", "personal_loan"

    # Generic deposit detection
    if re.search(r'\bdeposit\b|\bsave\b|\bsavings\b|\binvest\b|\bkeep\b', text_lower):
        return "deposit", "savings"

    return None, None


def extract_priority(text: str) -> Optional[str]:
    """Extract user priority from query."""
    text_lower = text.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return priority
    return None


def extract_country(text: str, default: str = "BD") -> str:
    """Extract country code from query text."""
    text_upper = text.upper()
    for code, info in COUNTRY_REGISTRY.items():
        if code in text_upper or info["name"].lower() in text.lower():
            return code
    return default


def extract_is_islamic(text: str) -> Optional[bool]:
    """Detect Islamic finance preference."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["islamic", "shariah", "sharia", "halal",
                                        "profit rate", "murabaha", "ijara", "islami"]):
        return True
    if any(kw in text_lower for kw in ["interest", "conventional", "non-islamic"]):
        return False
    return None


def extract_employment(text: str) -> Optional[str]:
    """Extract employment type."""
    text_lower = text.lower()
    for emp_type, keywords in EMPLOYMENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return emp_type
    return None


def extract_age(text: str) -> Optional[int]:
    """Extract age from query."""
    match = re.search(r'\b(\d{2})\s*(?:year|yr|বছর)?\s*(?:old|age|বয়স)', text.lower())
    if match:
        age = int(match.group(1))
        if 18 <= age <= 80:
            return age
    return None


def extract_income(text: str) -> Optional[float]:
    """Extract monthly income."""
    match = re.search(
        r'(?:earn|income|salary|মাসিক|monthly)[^\d]*([\d,]+)',
        text.lower()
    )
    if match:
        return float(match.group(1).replace(',', ''))
    return None


# ── Main Intent Extraction ─────────────────────────────────────────────────────

@dataclass
class Intent:
    country_code: str
    country_name: str
    currency_code: str
    currency_symbol: str
    product_category: Optional[str] = None
    product_type: Optional[str] = None
    amount: Optional[float] = None
    tenure_months: Optional[int] = None
    priority: Optional[str] = None
    is_islamic: Optional[bool] = None
    user_profile: dict = field(default_factory=dict)
    special_requirements: list = field(default_factory=list)
    missing_critical: list = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def extract_intent(query: str, default_country: str = "BD") -> Intent:
    """Extract structured intent from a natural language financial query."""

    country_code = extract_country(query, default_country)
    country_info = COUNTRY_REGISTRY.get(country_code, COUNTRY_REGISTRY["BD"])

    category, subcategory = extract_product_type(query)
    amount = extract_amount(query)
    tenure = extract_tenure(query)
    priority = extract_priority(query)
    is_islamic = extract_is_islamic(query)
    employment = extract_employment(query)
    age = extract_age(query)
    income = extract_income(query)

    user_profile = {}
    if age is not None:
        user_profile["age"] = age
    if income is not None:
        user_profile["monthly_income"] = income
    if employment is not None:
        user_profile["employment_type"] = employment

    # Determine missing critical fields
    missing = []
    if category == "loan":
        if amount is None:
            missing.append("amount")
        if tenure is None:
            missing.append("tenure_months")
    elif category == "deposit":
        if subcategory == "fdr" and tenure is None:
            missing.append("tenure_months")
        if amount is None:
            missing.append("amount")

    # Confidence score
    found_fields = sum([
        category is not None,
        subcategory is not None,
        amount is not None,
        tenure is not None,
        priority is not None,
    ])
    confidence = round(found_fields / 5.0, 2)

    return Intent(
        country_code=country_code,
        country_name=country_info["name"],
        currency_code=country_info["currency"],
        currency_symbol=country_info["symbol"],
        product_category=category,
        product_type=subcategory,
        amount=amount,
        tenure_months=tenure,
        priority=priority,
        is_islamic=is_islamic,
        user_profile=user_profile,
        special_requirements=[],
        missing_critical=missing,
        confidence=confidence,
    )


def get_clarification_questions(intent: Intent) -> list[str]:
    """Return minimum necessary clarification questions."""
    questions = []
    if "amount" in intent.missing_critical:
        sym = intent.currency_symbol
        if intent.product_category == "loan":
            questions.append(f"How much would you like to borrow? (e.g., {sym}5,00,000)")
        else:
            questions.append(f"How much would you like to deposit? (e.g., {sym}5,00,000)")
    if "tenure_months" in intent.missing_critical:
        if intent.product_category == "loan":
            questions.append("Over how many months/years would you like to repay?")
        else:
            questions.append("For how many months/years would you like to keep the deposit?")
    if intent.priority is None and intent.product_category == "loan":
        questions.append(
            "What matters most to you? "
            "(a) Lowest total cost, (b) Lowest monthly payment, or (c) Easiest to qualify for?"
        )
    return questions[:3]  # Maximum 3 questions


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="COMPARE AI Intent Agent")
    parser.add_argument("query", nargs="?", help="Natural language query")
    parser.add_argument("--query", "-q", dest="query_flag", help="Natural language query")
    parser.add_argument("--country", default="BD", help="Default country code (BD, IN, PK...)")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    query = args.query or args.query_flag
    if not query:
        print("Usage: intent_agent.py \"I need a personal loan of 5 lakh for 5 years\"")
        sys.exit(1)

    intent = extract_intent(query, args.country)
    result = intent.to_dict()
    clarifications = get_clarification_questions(intent)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("\n── COMPARE AI Intent Extraction ──────────────────────────")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if clarifications:
        print("\n── Clarification Questions Needed ─────────────────────────")
        for i, q in enumerate(clarifications, 1):
            print(f"  {i}. {q}")
    else:
        print("\n✓ Sufficient information — ready to begin research.")

    print(f"\nExtraction confidence: {intent.confidence:.0%}")


if __name__ == "__main__":
    main()
