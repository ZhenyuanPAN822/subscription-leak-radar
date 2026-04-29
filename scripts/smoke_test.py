from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from subscription_leak_radar.analyzer import (
    analyze_subscriptions,
    detect_subscriptions,
    parse_csv_transactions,
    parse_text_transactions,
    save_outputs,
)


def main() -> None:
    sample = ROOT / "samples" / "sample_transactions_90_days.csv"
    transactions, metadata = parse_csv_transactions(sample.read_text(encoding="utf-8"))
    if metadata["transaction_count"] < 40:
        raise SystemExit("sample did not parse enough transactions")
    text_transactions, text_metadata = parse_text_transactions((ROOT / "examples" / "statement_paste.txt").read_text(encoding="utf-8"))
    if text_metadata["transaction_count"] < 6:
        raise SystemExit("text paste parser did not extract expected transactions")
    detected = detect_subscriptions(transactions + text_transactions)
    report = analyze_subscriptions(detected, today="2026-04-29")
    if report["summary"]["subscription_count"] < 8:
        raise SystemExit("not enough subscriptions detected")
    paths = save_outputs(report, ROOT / "outputs")
    for path in paths.values():
        if not Path(path).exists():
            raise SystemExit(f"missing output: {path}")
    print("Smoke test passed: CSV import, text paste parser, recurrence detection, and report export work.")


if __name__ == "__main__":
    main()
