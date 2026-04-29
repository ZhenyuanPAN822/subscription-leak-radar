import unittest
from pathlib import Path

from subscription_leak_radar.analyzer import (
    ManualSubscription,
    analyze_subscriptions,
    detect_subscriptions,
    parse_csv_transactions,
    parse_text_transactions,
)


class AnalyzerTests(unittest.TestCase):
    def test_flexible_csv_mapping(self):
        csv_text = "posted_date,payee,debit,currency\n2026-01-01,Netflix,15.49,USD\n2026-02-01,Netflix,15.49,USD\n"
        transactions, metadata = parse_csv_transactions(csv_text)
        self.assertEqual(len(transactions), 2)
        self.assertEqual(metadata["detected_columns"]["description"], "payee")

    def test_missing_csv_fields_are_helpful(self):
        with self.assertRaisesRegex(ValueError, "Missing required CSV fields"):
            parse_csv_transactions("date,notes\n2026-01-01,Netflix\n")

    def test_text_paste_parser_rejects_malformed_lines(self):
        transactions, metadata = parse_text_transactions("2026-01-01 NETFLIX $15.49\nbad line\n2026-02-01 NETFLIX $15.49")
        self.assertEqual(len(transactions), 2)
        self.assertEqual(len(metadata["rejected_lines"]), 1)

    def test_recurring_detection_and_price_change(self):
        csv_text = "date,description,amount\n2026-01-01,Netflix,-15.49\n2026-02-01,Netflix,-15.49\n2026-03-01,Netflix,-17.99\n"
        transactions, _ = parse_csv_transactions(csv_text)
        detected = detect_subscriptions(transactions)
        self.assertEqual(len(detected), 1)
        self.assertEqual(detected[0].cadence, "monthly")
        self.assertGreater(detected[0].price_change_percent, 10)

    def test_manual_subscription_is_included(self):
        detected = detect_subscriptions([], [ManualSubscription(merchant="Local Gym", amount=45)])
        self.assertEqual(len(detected), 1)
        self.assertIn("manual_entry", detected[0].review_flags)

    def test_sample_has_many_transactions_and_report(self):
        sample = Path(__file__).resolve().parents[1] / "samples" / "sample_transactions_90_days.csv"
        transactions, _ = parse_csv_transactions(sample.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(transactions), 40)
        report = analyze_subscriptions(detect_subscriptions(transactions), today="2026-04-29")
        self.assertGreaterEqual(report["summary"]["subscription_count"], 8)
        self.assertGreater(report["summary"]["annualized_cost"], 1000)
        self.assertIn("cancel_top_3", report["savings_scenarios"])

    def test_duplicate_category_flags(self):
        csv_text = """date,description,amount
2026-01-01,OPENAI CHATGPT,-20
2026-02-01,OPENAI CHATGPT,-20
2026-01-03,ANTHROPIC CLAUDE,-20
2026-02-03,ANTHROPIC CLAUDE,-20
"""
        transactions, _ = parse_csv_transactions(csv_text)
        detected = detect_subscriptions(transactions)
        self.assertTrue(any(item.duplicate_cluster == "ai-tools" for item in detected))


if __name__ == "__main__":
    unittest.main()

