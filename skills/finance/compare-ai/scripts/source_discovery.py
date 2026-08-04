#!/usr/bin/env python3
"""
COMPARE AI — Source Discovery (Bangladesh Plugin)

Returns prioritized list of official URLs to check per institution and product type.
Extends to global via country plugin pattern.

Usage:
    python3 source_discovery.py --country BD --product personal_loan
    python3 source_discovery.py --country BD --product fdr --institution "BRAC Bank"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class SourceTarget:
    institution: str
    institution_type: str      # bank | nbfi | mfi | regulator
    url: str
    source_type: str           # official_product_page | official_rate_sheet | official_pdf | ...
    tier: int
    priority: int              # lower = check first
    search_query: str          # suggested search query if URL fails
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ── Bangladesh Institution Registry ──────────────────────────────────────────

BD_INSTITUTIONS = {
    # State-owned Banks
    "sonali_bank": {
        "name": "Sonali Bank PLC",
        "type": "bank",
        "subtype": "state_owned",
        "website": "https://www.sonalibank.com.bd",
        "product_paths": {
            "personal_loan": "/retail-banking/personal-loan",
            "home_loan": "/retail-banking/home-loan",
            "savings": "/retail-banking/savings-account",
            "fdr": "/retail-banking/fdr",
            "dps": "/retail-banking/dps",
        },
        "rate_sheet_path": "/interest-rate",
        "is_islamic": False,
    },
    "janata_bank": {
        "name": "Janata Bank PLC",
        "type": "bank",
        "subtype": "state_owned",
        "website": "https://www.janatabank-bd.com",
        "product_paths": {
            "personal_loan": "/products/personal-loan",
            "savings": "/products/savings",
            "fdr": "/products/fdr",
            "dps": "/products/dps",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
    "agrani_bank": {
        "name": "Agrani Bank PLC",
        "type": "bank",
        "subtype": "state_owned",
        "website": "https://www.agranibank.org",
        "product_paths": {
            "personal_loan": "/loan/personal-loan",
            "savings": "/deposit/savings",
            "fdr": "/deposit/fdr",
        },
        "rate_sheet_path": "/interest-rate",
        "is_islamic": False,
    },
    # Private Banks
    "dutch_bangla": {
        "name": "Dutch-Bangla Bank PLC",
        "type": "bank",
        "subtype": "private",
        "website": "https://www.dutchbanglabank.com",
        "product_paths": {
            "personal_loan": "/personal-banking/loans/personal-loan",
            "home_loan": "/personal-banking/loans/home-loan",
            "auto_loan": "/personal-banking/loans/auto-loan",
            "savings": "/personal-banking/deposits/savings-account",
            "fdr": "/personal-banking/deposits/fdr",
            "dps": "/personal-banking/deposits/dps",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
    "brac_bank": {
        "name": "BRAC Bank PLC",
        "type": "bank",
        "subtype": "private",
        "website": "https://www.bracbank.com",
        "product_paths": {
            "personal_loan": "/personal/loans/personal-loan",
            "home_loan": "/personal/loans/home-loan",
            "auto_loan": "/personal/loans/auto-loan",
            "savings": "/personal/deposits/savings-account",
            "fdr": "/personal/deposits/fdr",
            "dps": "/personal/deposits/dps",
        },
        "rate_sheet_path": "/rates",
        "is_islamic": False,
    },
    "city_bank": {
        "name": "The City Bank PLC",
        "type": "bank",
        "subtype": "private",
        "website": "https://www.thecitybank.com",
        "product_paths": {
            "personal_loan": "/personal-banking/loans/personal-loan",
            "home_loan": "/personal-banking/loans/home-loan",
            "savings": "/personal-banking/deposits/savings-account",
            "fdr": "/personal-banking/deposits/fdr",
            "dps": "/personal-banking/deposits/dps",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
    "eastern_bank": {
        "name": "Eastern Bank PLC",
        "type": "bank",
        "subtype": "private",
        "website": "https://www.ebl.com.bd",
        "product_paths": {
            "personal_loan": "/personal/loans",
            "home_loan": "/personal/loans/home-loan",
            "savings": "/personal/deposits",
            "fdr": "/personal/deposits/fdr",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
    "mutual_trust": {
        "name": "Mutual Trust Bank PLC",
        "type": "bank",
        "subtype": "private",
        "website": "https://www.mutualtrustbank.com",
        "product_paths": {
            "personal_loan": "/personal-banking/loans",
            "savings": "/personal-banking/deposits",
            "fdr": "/personal-banking/deposits/fdr",
            "dps": "/personal-banking/deposits/dps",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
    "prime_bank": {
        "name": "Prime Bank PLC",
        "type": "bank",
        "subtype": "private",
        "website": "https://www.primebank.com.bd",
        "product_paths": {
            "personal_loan": "/personal-banking/loan-products",
            "home_loan": "/personal-banking/home-loan",
            "savings": "/personal-banking/deposit-products",
            "fdr": "/personal-banking/fixed-deposit",
            "dps": "/personal-banking/dps",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
    # Islamic Banks
    "islami_bank": {
        "name": "Islami Bank Bangladesh PLC",
        "type": "bank",
        "subtype": "islamic",
        "website": "https://www.islamibankbd.com",
        "product_paths": {
            "personal_loan": "/personal-banking/investment-products",
            "home_loan": "/personal-banking/home-investment",
            "savings": "/personal-banking/deposits/mudaraba-savings",
            "fdr": "/personal-banking/deposits/mudaraba-term-deposit",
            "dps": "/personal-banking/deposits/mudaraba-savings-bond",
        },
        "rate_sheet_path": "/profit-rate",
        "is_islamic": True,
    },
    "shahjalal_islami": {
        "name": "Shahjalal Islami Bank PLC",
        "type": "bank",
        "subtype": "islamic",
        "website": "https://www.sjiblbd.com",
        "product_paths": {
            "personal_loan": "/personal/investment",
            "savings": "/personal/deposit",
            "fdr": "/personal/deposit/mudaraba-term-deposit",
        },
        "rate_sheet_path": "/profit-rate",
        "is_islamic": True,
    },
    # NBFIs
    "idlc": {
        "name": "IDLC Finance PLC",
        "type": "nbfi",
        "subtype": "private",
        "website": "https://www.idlc.com",
        "product_paths": {
            "personal_loan": "/personal/loans",
            "home_loan": "/personal/home-loan",
            "fdr": "/personal/deposits/fixed-deposit",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
    "ipdc": {
        "name": "IPDC Finance PLC",
        "type": "nbfi",
        "subtype": "private",
        "website": "https://www.ipdc.com.bd",
        "product_paths": {
            "personal_loan": "/personal/loans",
            "home_loan": "/personal/home-loan",
            "fdr": "/personal/deposits",
        },
        "rate_sheet_path": "/rates",
        "is_islamic": False,
    },
    "lankabangla": {
        "name": "LankaBangla Finance PLC",
        "type": "nbfi",
        "subtype": "private",
        "website": "https://www.lankabangla.com",
        "product_paths": {
            "personal_loan": "/personal/loans/personal-loan",
            "home_loan": "/personal/loans/home-loan",
            "fdr": "/personal/deposit/fdr",
        },
        "rate_sheet_path": "/interest-rates",
        "is_islamic": False,
    },
}

# Regulators
BD_REGULATORS = {
    "bangladesh_bank": {
        "name": "Bangladesh Bank",
        "url": "https://www.bb.org.bd",
        "rate_circulars": "https://www.bb.org.bd/en/index.php/mediaroom/circulars",
        "interest_rate_page": "https://www.bb.org.bd/en/index.php/econdata/interestrate",
    },
    "mra": {
        "name": "Microcredit Regulatory Authority",
        "url": "https://mra.gov.bd",
    },
}

# Search query templates per product type
SEARCH_TEMPLATES = {
    "personal_loan": [
        '"{institution}" "personal loan" "interest rate" site:{domain}',
        '"{institution}" personal loan Bangladesh rate',
        'site:{domain} personal loan rate sheet filetype:pdf',
        '"{institution}" personal loan eligibility Bangladesh',
    ],
    "home_loan": [
        '"{institution}" "home loan" "interest rate" site:{domain}',
        '"{institution}" mortgage Bangladesh rate',
        'site:{domain} home loan rate',
    ],
    "fdr": [
        '"{institution}" "fixed deposit" rate site:{domain}',
        '"{institution}" FDR interest rate Bangladesh',
        'site:{domain} FDR rate filetype:pdf',
    ],
    "dps": [
        '"{institution}" "deposit pension" rate site:{domain}',
        '"{institution}" DPS monthly savings Bangladesh',
        'site:{domain} DPS rate',
    ],
    "savings": [
        '"{institution}" "savings account" "interest rate" site:{domain}',
        '"{institution}" savings account Bangladesh rate',
        'site:{domain} savings account rate',
    ],
}


def get_source_targets(
    country: str = "BD",
    product_type: str = "personal_loan",
    institution_filter: Optional[str] = None,
    is_islamic: Optional[bool] = None,
    limit: int = 20,
) -> list[SourceTarget]:
    """
    Return prioritized list of source URLs to check.
    """
    if country != "BD":
        # Stub for future country plugins
        return []

    institutions = BD_INSTITUTIONS

    # Filter by institution name
    if institution_filter:
        filter_lower = institution_filter.lower()
        institutions = {
            k: v for k, v in institutions.items()
            if filter_lower in v["name"].lower() or filter_lower in k.lower()
        }

    # Filter by Islamic preference
    if is_islamic is not None:
        institutions = {
            k: v for k, v in institutions.items()
            if v.get("is_islamic") == is_islamic
        }

    targets = []
    priority = 1

    # Add regulator sources first (Tier 1)
    if product_type in ("personal_loan", "home_loan"):
        bb = BD_REGULATORS["bangladesh_bank"]
        targets.append(SourceTarget(
            institution="Bangladesh Bank",
            institution_type="regulator",
            url=bb["interest_rate_page"],
            source_type="regulatory",
            tier=1,
            priority=priority,
            search_query=f"Bangladesh Bank interest rate cap {product_type.replace('_', ' ')}",
            notes="Check for any interest rate caps or circulars",
        ))
        priority += 1

    # Add institution-specific sources (Tier 2 & 3)
    for inst_key, inst in institutions.items():
        domain = inst["website"].replace("https://", "").replace("http://", "").rstrip("/")
        product_path = inst.get("product_paths", {}).get(product_type)
        rate_path = inst.get("rate_sheet_path")

        # Product page (Tier 2)
        if product_path:
            targets.append(SourceTarget(
                institution=inst["name"],
                institution_type=inst["type"],
                url=inst["website"] + product_path,
                source_type="official_product_page",
                tier=2,
                priority=priority,
                search_query=SEARCH_TEMPLATES.get(product_type, [""])[0].format(
                    institution=inst["name"], domain=domain
                ),
                notes="Official product page",
            ))
            priority += 1

        # Rate sheet page (Tier 2)
        if rate_path:
            targets.append(SourceTarget(
                institution=inst["name"],
                institution_type=inst["type"],
                url=inst["website"] + rate_path,
                source_type="official_rate_sheet",
                tier=2,
                priority=priority,
                search_query=f'site:{domain} interest rate sheet',
                notes="Official rate sheet",
            ))
            priority += 1

        # PDF rate sheet (Tier 3)
        targets.append(SourceTarget(
            institution=inst["name"],
            institution_type=inst["type"],
            url=inst["website"],
            source_type="official_pdf",
            tier=3,
            priority=priority,
            search_query=f'site:{domain} filetype:pdf {product_type.replace("_", " ")} rate',
            notes="Search for PDF rate sheets",
        ))
        priority += 1

    # Sort by tier then priority
    targets.sort(key=lambda t: (t.tier, t.priority))
    return targets[:limit]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="COMPARE AI Source Discovery")
    parser.add_argument("--country", default="BD")
    parser.add_argument("--product", default="personal_loan",
                        choices=["personal_loan", "home_loan", "auto_loan", "sme_loan",
                                 "savings", "fdr", "dps", "education_loan"])
    parser.add_argument("--institution", help="Filter by institution name")
    parser.add_argument("--islamic", type=str, choices=["yes", "no"],
                        help="Filter Islamic/conventional")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    is_islamic = None
    if args.islamic == "yes":
        is_islamic = True
    elif args.islamic == "no":
        is_islamic = False

    targets = get_source_targets(
        country=args.country,
        product_type=args.product,
        institution_filter=args.institution,
        is_islamic=is_islamic,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps([t.to_dict() for t in targets], indent=2, ensure_ascii=False))
    else:
        print(f"\n── Source Targets: {args.country} / {args.product} ({len(targets)}) ──────")
        for t in targets:
            print(f"\n  [{t.tier}] {t.institution} ({t.source_type})")
            print(f"       URL:   {t.url}")
            print(f"       Query: {t.search_query}")
            if t.notes:
                print(f"       Note:  {t.notes}")


if __name__ == "__main__":
    main()
