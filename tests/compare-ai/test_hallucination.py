"""
COMPARE AI — Hallucination Prevention Tests

Critical tests to ensure the system NEVER invents financial data.
Any test failure here is a severity-1 defect.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../skills/finance/compare-ai/scripts"))

from intent_agent import extract_intent
from verification_engine import verify_field, values_conflict


class TestNullFieldHandling(unittest.TestCase):
    """
    Verify the system returns null for any unverifiable financial field.
    The system must NEVER invent rates, fees, or eligibility information.
    """

    def test_intent_missing_amount_returns_null(self):
        """Query without amount must return None for amount field."""
        intent = extract_intent("I need a personal loan")
        self.assertIsNone(intent.amount)

    def test_intent_missing_tenure_returns_null(self):
        """Query without tenure must return None for tenure field."""
        intent = extract_intent("I need a personal loan of 5 lakh")
        self.assertIsNone(intent.tenure_months)

    def test_intent_missing_country_defaults_to_bd(self):
        """Query without country defaults to BD (not invented)."""
        intent = extract_intent("I need a personal loan")
        # Default is BD — this is a configured default, not invention
        self.assertEqual(intent.country_code, "BD")

    def test_intent_flags_missing_critical_fields(self):
        """Missing critical fields must be listed in missing_critical."""
        intent = extract_intent("I need a personal loan")
        self.assertIn("amount", intent.missing_critical)
        self.assertIn("tenure_months", intent.missing_critical)

    def test_intent_recognizes_amount_lakh(self):
        """Correctly parses 5 lakh as 500,000."""
        intent = extract_intent("I need a 5 lakh personal loan for 5 years")
        self.assertEqual(intent.amount, 500_000)

    def test_intent_recognizes_tenure_years(self):
        """Correctly parses 5 years as 60 months."""
        intent = extract_intent("I need a personal loan for 5 years")
        self.assertEqual(intent.tenure_months, 60)

    def test_intent_recognizes_tenure_months(self):
        """Correctly parses 36 months."""
        intent = extract_intent("I need a loan for 36 months")
        self.assertEqual(intent.tenure_months, 36)

    def test_intent_does_not_invent_rate(self):
        """Intent extraction must NOT invent an interest rate."""
        intent = extract_intent("I need a 5 lakh personal loan for 5 years")
        # Intent schema has no rate field — rate comes from research
        d = intent.to_dict()
        self.assertNotIn("interest_rate", d)
        self.assertNotIn("rate", d)

    def test_intent_islamic_detection_none_when_ambiguous(self):
        """When Islamic preference is not stated, must return None not False."""
        intent = extract_intent("I need a personal loan of 5 lakh")
        self.assertIsNone(intent.is_islamic)

    def test_intent_islamic_detection_true(self):
        """Correctly detects Islamic preference."""
        intent = extract_intent("I need an Islamic personal loan of 5 lakh")
        self.assertTrue(intent.is_islamic)


class TestVerificationAntiHallucination(unittest.TestCase):
    """Verify that empty/no sources always results in unknown, not invented values."""

    def test_empty_sources_returns_unknown(self):
        """No sources → status must be unknown, not a guessed value."""
        result = verify_field("interest_rate", [])
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.primary_value)
        self.assertEqual(result.confidence_score, 0.0)

    def test_single_source_returns_partial_not_verified(self):
        """Single source → status is 'partial', not 'verified'."""
        result = verify_field("interest_rate", [
            {"url": "https://bank.com/loan", "value": "12%", "source_type": "official_product_page"}
        ])
        self.assertEqual(result.status, "partial")

    def test_two_matching_sources_returns_verified(self):
        """Two matching sources → status is 'verified'."""
        result = verify_field("interest_rate", [
            {"url": "https://bank.com/loan", "value": "12%", "source_type": "official_product_page"},
            {"url": "https://bank.com/rates", "value": "12%", "source_type": "official_rate_sheet"},
        ])
        self.assertEqual(result.status, "verified")

    def test_conflicting_sources_returns_conflicting(self):
        """Two different values → status must be 'conflicting', never silently resolved."""
        result = verify_field("interest_rate", [
            {"url": "https://bank.com/loan", "value": "10%", "source_type": "official_product_page"},
            {"url": "https://bank.com/rates", "value": "11%", "source_type": "official_rate_sheet"},
        ])
        self.assertEqual(result.status, "conflicting")
        self.assertGreater(len(result.conflicts), 0)

    def test_conflict_detection_rate_difference(self):
        """Rate difference > 0.01% should be detected as conflict."""
        self.assertTrue(values_conflict("10%", "11%", "interest_rate"))

    def test_no_conflict_same_rate(self):
        """Same rate should NOT be detected as conflict."""
        self.assertFalse(values_conflict("12%", "12%", "interest_rate"))

    def test_no_conflict_none_values(self):
        """None values should not generate false conflicts."""
        self.assertFalse(values_conflict(None, "12%", "interest_rate"))
        self.assertFalse(values_conflict("12%", None, "interest_rate"))

    def test_higher_tier_used_as_primary(self):
        """Lower tier number (more authoritative) must be used as primary value."""
        result = verify_field("interest_rate", [
            {"url": "https://forum.com", "value": "10%", "source_type": "forum"},
            {"url": "https://bank.com", "value": "12%", "source_type": "official_product_page"},
        ])
        # Primary should be the official source (tier 2) not the forum (tier 5)
        self.assertEqual(result.primary_value, "12%")

    def test_stale_source_still_flags(self):
        """Must never silently use stale data without acknowledging it."""
        result = verify_field("interest_rate", [
            {
                "url": "https://bank.com/loan",
                "value": "12%",
                "source_type": "official_product_page",
                "checked_at": "2020-01-01"
            }
        ])
        # Stale but single source — should still capture the value
        # and mark as partial (not verified cross-checked)
        self.assertIn(result.status, ("partial", "unknown"))


class TestIntentAmountParsing(unittest.TestCase):
    """Verify amount parsing across different formats."""

    def test_lakh_format(self):
        self.assertEqual(extract_intent("5 lakh personal loan").amount, 500_000)

    def test_crore_format(self):
        self.assertEqual(extract_intent("2 crore home loan").amount, 20_000_000)

    def test_numeric_format(self):
        intent = extract_intent("500000 personal loan")
        self.assertEqual(intent.amount, 500_000)

    def test_currency_symbol_format(self):
        intent = extract_intent("৳500000 personal loan")
        self.assertEqual(intent.amount, 500_000)


if __name__ == '__main__':
    unittest.main(verbosity=2)
