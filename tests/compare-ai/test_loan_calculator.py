"""
COMPARE AI — Loan Calculator Tests

Tests deterministic EMI calculations against known values.
All math must be reproducible and verifiable.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../skills/finance/compare-ai/scripts"))

from loan_calculator import calculate_emi, calculate_loan


class TestEMIFormula(unittest.TestCase):
    """Test the core EMI formula against known/reference values."""

    def test_standard_emi_500k_12pct_60months(self):
        """
        ৳5,00,000 at 12% p.a. for 60 months.
        Reference: Standard amortization table.
        """
        emi = calculate_emi(500_000, 12.0, 60)
        # Expected: ~11,122 BDT (verified against amortization tables)
        self.assertAlmostEqual(emi, 11_122, delta=2)

    def test_standard_emi_100k_10pct_12months(self):
        emi = calculate_emi(100_000, 10.0, 12)
        # Monthly rate = 10/12/100 = 0.008333
        # EMI = 100000 * 0.008333 * (1.008333^12) / (1.008333^12 - 1)
        self.assertAlmostEqual(emi, 8791, delta=2)

    def test_zero_interest_loan(self):
        """Zero-interest loan should divide principal equally."""
        emi = calculate_emi(120_000, 0.0, 12)
        self.assertAlmostEqual(emi, 10_000, delta=1)

    def test_total_payment_exceeds_principal(self):
        """Total payment must always exceed principal for interest > 0."""
        result = calculate_loan(500_000, 12.0, 60)
        self.assertGreater(result.total_payment, 500_000)

    def test_total_interest_positive(self):
        """Total interest must be positive."""
        result = calculate_loan(500_000, 12.0, 60)
        self.assertGreater(result.total_interest, 0)

    def test_total_payment_equals_emi_times_tenure(self):
        """Total payment = EMI × tenure (within rounding)."""
        result = calculate_loan(500_000, 12.0, 60)
        expected = result.monthly_installment * 60
        self.assertAlmostEqual(result.total_payment, expected, delta=2)

    def test_fees_add_to_total_cost(self):
        """Total cost = total payment + known fees."""
        result = calculate_loan(500_000, 12.0, 60, processing_fee_flat=5000, documentation_fee=1000)
        self.assertAlmostEqual(result.estimated_total_cost, result.total_payment + 6000, delta=1)

    def test_processing_fee_pct(self):
        """Processing fee as % of principal calculated correctly."""
        result = calculate_loan(500_000, 12.0, 60, processing_fee_pct=1.0)
        self.assertAlmostEqual(result.processing_fee_pct_amount, 5_000, delta=1)

    def test_higher_rate_higher_total_cost(self):
        """Higher rate should always result in higher total cost."""
        result_low = calculate_loan(500_000, 10.0, 60)
        result_high = calculate_loan(500_000, 15.0, 60)
        self.assertGreater(result_high.total_payment, result_low.total_payment)

    def test_longer_tenure_higher_total_interest(self):
        """Longer tenure = more total interest paid."""
        result_short = calculate_loan(500_000, 12.0, 36)
        result_long = calculate_loan(500_000, 12.0, 60)
        self.assertGreater(result_long.total_interest, result_short.total_interest)

    def test_longer_tenure_lower_monthly_payment(self):
        """Longer tenure = lower monthly payment."""
        result_short = calculate_loan(500_000, 12.0, 36)
        result_long = calculate_loan(500_000, 12.0, 60)
        self.assertLess(result_long.monthly_installment, result_short.monthly_installment)

    def test_calculation_label_present(self):
        """Result must always include calculation label."""
        result = calculate_loan(500_000, 12.0, 60)
        self.assertTrue(bool(result.calculation_label))
        self.assertIn("published", result.calculation_label.lower())

    def test_disclaimer_present(self):
        """Result must always include disclaimer."""
        result = calculate_loan(500_000, 12.0, 60)
        self.assertTrue(bool(result.disclaimer))
        self.assertIn("not an official", result.disclaimer.lower())

    def test_million_loan(self):
        """Test with ৳10,00,000 at 9.5% for 84 months."""
        emi = calculate_emi(1_000_000, 9.5, 84)
        # Monthly rate = 9.5/12/100 = 0.007917
        self.assertGreater(emi, 0)
        total = emi * 84
        self.assertGreater(total, 1_000_000)

    def test_output_dict_contains_all_fields(self):
        """Result dict must contain all required fields."""
        result = calculate_loan(500_000, 12.0, 60)
        d = result.to_dict()
        required_keys = [
            'principal', 'annual_rate_pct', 'tenure_months',
            'monthly_installment', 'total_payment', 'total_interest',
            'estimated_total_cost', 'calculation_label', 'disclaimer',
        ]
        for key in required_keys:
            self.assertIn(key, d, f"Missing key: {key}")


class TestHallucinationPrevention(unittest.TestCase):
    """Verify calculator never invents values."""

    def test_no_rate_means_no_emi(self):
        """If rate is None/0, result should be explicitly zero-rate."""
        emi = calculate_emi(500_000, 0.0, 60)
        # Should be exactly principal / tenure
        self.assertAlmostEqual(emi, 500_000 / 60, delta=0.1)

    def test_result_confidence_is_calculated_not_estimated(self):
        """Confidence field must say 'calculated' not 'estimated'."""
        result = calculate_loan(500_000, 12.0, 60)
        self.assertEqual(result.confidence, 'calculated')


if __name__ == '__main__':
    unittest.main(verbosity=2)
