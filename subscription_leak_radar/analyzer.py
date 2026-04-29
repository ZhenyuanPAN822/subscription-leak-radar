from __future__ import annotations

import csv
import io
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Iterable


DATE_COLUMNS = ("date", "posted_date", "transaction_date", "trans_date", "purchase_date", "created_at")
DESCRIPTION_COLUMNS = ("description", "merchant", "name", "payee", "transaction", "memo", "details")
AMOUNT_COLUMNS = ("amount", "transaction_amount", "charge", "debit", "withdrawal", "spent")
CURRENCY_COLUMNS = ("currency", "ccy")
ACCOUNT_COLUMNS = ("account", "account_name", "card", "source")

COMMON_CATALOG = {
    "netflix": ("streaming", "https://www.netflix.com/cancelplan"),
    "spotify": ("music", "https://www.spotify.com/account/subscription/"),
    "hulu": ("streaming", "https://help.hulu.com/article/hulu-cancel-subscription"),
    "disney": ("streaming", "https://help.disneyplus.com/article/disneyplus-cancel"),
    "apple": ("app-store", "https://support.apple.com/billing"),
    "google": ("app-store", "https://play.google.com/store/account/subscriptions"),
    "adobe": ("creative-software", "https://account.adobe.com/plans"),
    "dropbox": ("cloud-storage", "https://www.dropbox.com/account/plan"),
    "notion": ("productivity", "https://www.notion.so/help/upgrade-or-downgrade-your-plan"),
    "openai": ("ai-tools", "https://help.openai.com/"),
    "anthropic": ("ai-tools", "https://support.anthropic.com/"),
    "canva": ("creative-software", "https://www.canva.com/help/cancel-subscription/"),
    "github": ("developer-tools", "https://github.com/settings/billing"),
    "amazon prime": ("shopping", "https://www.amazon.com/amazonprime"),
    "audible": ("books-audio", "https://www.audible.com/account/cancel"),
    "gym": ("fitness", ""),
    "peloton": ("fitness", "https://support.onepeloton.com/"),
}


@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    currency: str = "USD"
    account: str = ""
    source: str = "csv"
    raw: dict | None = None


@dataclass
class ManualSubscription:
    merchant: str
    amount: float
    currency: str = "USD"
    cadence: str = "monthly"
    next_renewal: str = ""
    category: str = "uncategorized"
    notes: str = ""


@dataclass
class DetectedSubscription:
    merchant: str
    merchant_key: str
    category: str
    cadence: str
    confidence: float
    latest_amount: float
    average_amount: float
    annualized_cost: float
    currency: str
    first_seen: str
    last_seen: str
    next_renewal_estimate: str
    transaction_count: int
    price_change_percent: float
    duplicate_cluster: str
    cancellation_url: str
    review_flags: list[str]
    source: str
    transactions: list[dict]


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def find_column(headers: Iterable[str], candidates: Iterable[str]) -> str | None:
    normalized = {normalize_header(header): header for header in headers}
    for candidate in candidates:
        key = normalize_header(candidate)
        if key in normalized:
            return normalized[key]
    return None


def parse_date(value: str) -> date:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    raise ValueError(f"Could not parse date: {value!r}")


def parse_amount(value: str | float | int) -> float:
    if isinstance(value, (int, float)):
        return abs(float(value))
    text = str(value or "").strip()
    if not text:
        return 0.0
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if cleaned in ("", "-", "."):
        return 0.0
    amount = float(cleaned)
    if negative:
        amount = -abs(amount)
    return abs(amount)


def normalize_merchant(description: str) -> str:
    text = description.lower()
    text = re.sub(r"\b(pos|debit|card|purchase|payment|recurring|subscription|online|inc|llc|ltd|co)\b", " ", text)
    text = re.sub(r"\d{3,}", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for known in COMMON_CATALOG:
        if known in text:
            return known
    tokens = text.split()
    return " ".join(tokens[:3]) if tokens else "unknown merchant"


def title_merchant(key: str, descriptions: list[str]) -> str:
    for description in descriptions:
        clean = re.sub(r"\s+", " ", description).strip()
        if clean:
            return clean[:60]
    return key.title()


def catalog_for(key: str) -> tuple[str, str]:
    for known, value in COMMON_CATALOG.items():
        if known in key:
            return value
    return ("uncategorized", "")


def parse_csv_transactions(csv_text: str) -> tuple[list[Transaction], dict]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")

    headers = reader.fieldnames
    date_col = find_column(headers, DATE_COLUMNS)
    desc_col = find_column(headers, DESCRIPTION_COLUMNS)
    amount_col = find_column(headers, AMOUNT_COLUMNS)
    currency_col = find_column(headers, CURRENCY_COLUMNS)
    account_col = find_column(headers, ACCOUNT_COLUMNS)

    missing = []
    if not date_col:
        missing.append("date column such as date, posted_date, transaction_date")
    if not desc_col:
        missing.append("description column such as description, merchant, payee")
    if not amount_col:
        missing.append("amount column such as amount, charge, debit, withdrawal")
    if missing:
        raise ValueError("Missing required CSV fields: " + "; ".join(missing))

    transactions: list[Transaction] = []
    row_errors: list[str] = []
    for index, row in enumerate(reader, start=2):
        try:
            amount = parse_amount(row.get(amount_col, ""))
            if amount <= 0:
                continue
            transactions.append(
                Transaction(
                    date=parse_date(row.get(date_col, "")).isoformat(),
                    description=str(row.get(desc_col, "")).strip(),
                    amount=amount,
                    currency=(row.get(currency_col, "") if currency_col else "USD") or "USD",
                    account=(row.get(account_col, "") if account_col else ""),
                    source="csv",
                    raw=row,
                )
            )
        except Exception as exc:
            row_errors.append(f"row {index}: {exc}")

    return transactions, {
        "detected_columns": {
            "date": date_col,
            "description": desc_col,
            "amount": amount_col,
            "currency": currency_col,
            "account": account_col,
        },
        "transaction_count": len(transactions),
        "row_errors": row_errors[:10],
    }


TEXT_LINE_RE = re.compile(
    r"(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[/]\d{1,2}[/]\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})"
    r"(?P<body>.*?)"
    r"(?P<amount>[-(]?\$?\s?\d+[,\d]*(?:\.\d{2})?\)?)",
    re.IGNORECASE,
)


def parse_text_transactions(text: str) -> tuple[list[Transaction], dict]:
    transactions: list[Transaction] = []
    rejected: list[str] = []
    for line in text.splitlines():
        raw_line = line.strip()
        if not raw_line:
            continue
        match = TEXT_LINE_RE.search(raw_line)
        if not match:
            rejected.append(raw_line)
            continue
        body = re.sub(r"\s+", " ", match.group("body")).strip(" -:\t")
        if not body:
            body = "unknown merchant"
        try:
            transactions.append(
                Transaction(
                    date=parse_date(match.group("date")).isoformat(),
                    description=body,
                    amount=parse_amount(match.group("amount")),
                    currency="USD",
                    source="text-paste",
                    raw={"line": raw_line},
                )
            )
        except Exception as exc:
            rejected.append(f"{raw_line} ({exc})")
    return transactions, {"transaction_count": len(transactions), "rejected_lines": rejected[:10]}


def cadence_from_intervals(intervals: list[int]) -> tuple[str, float]:
    if not intervals:
        return ("unknown", 0.25)
    med = median(intervals)
    if 5 <= med <= 9:
        return ("weekly", 0.85)
    if 25 <= med <= 35:
        return ("monthly", 0.92)
    if 55 <= med <= 70:
        return ("bi-monthly", 0.75)
    if 80 <= med <= 100:
        return ("quarterly", 0.82)
    if 350 <= med <= 380:
        return ("annual", 0.78)
    return ("irregular", 0.45)


def annual_factor(cadence: str) -> float:
    return {
        "weekly": 52,
        "monthly": 12,
        "bi-monthly": 6,
        "quarterly": 4,
        "annual": 1,
    }.get(cadence, 4)


def estimate_next_date(last_seen: date, cadence: str) -> date:
    days = {
        "weekly": 7,
        "monthly": 30,
        "bi-monthly": 61,
        "quarterly": 91,
        "annual": 365,
    }.get(cadence, 30)
    return last_seen + timedelta(days=days)


def detect_subscriptions(transactions: list[Transaction], manual: list[ManualSubscription] | None = None) -> list[DetectedSubscription]:
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    for tx in transactions:
        grouped[normalize_merchant(tx.description)].append(tx)

    detected: list[DetectedSubscription] = []
    category_counts: Counter[str] = Counter()

    for key, rows in grouped.items():
        rows = sorted(rows, key=lambda tx: tx.date)
        if len(rows) < 2:
            continue
        dates = [parse_date(tx.date) for tx in rows]
        intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        cadence, cadence_confidence = cadence_from_intervals(intervals)
        if cadence == "irregular" and len(rows) < 3:
            continue

        amounts = [tx.amount for tx in rows]
        first_amount = amounts[0]
        latest_amount = amounts[-1]
        avg_amount = sum(amounts) / len(amounts)
        price_change = ((latest_amount - first_amount) / first_amount * 100) if first_amount else 0.0
        category, cancel_url = catalog_for(key)
        category_counts[category] += 1
        flags = []
        if cadence in ("unknown", "irregular"):
            flags.append("cadence_needs_review")
        if abs(price_change) >= 10:
            flags.append("price_changed")
        if len(set(round(amount, 2) for amount in amounts)) > 2:
            flags.append("variable_amount")
        confidence = min(0.98, cadence_confidence + min(len(rows), 6) * 0.04)
        detected.append(
            DetectedSubscription(
                merchant=title_merchant(key, [row.description for row in rows]),
                merchant_key=key,
                category=category,
                cadence=cadence,
                confidence=round(confidence, 2),
                latest_amount=round(latest_amount, 2),
                average_amount=round(avg_amount, 2),
                annualized_cost=round(latest_amount * annual_factor(cadence), 2),
                currency=rows[-1].currency,
                first_seen=dates[0].isoformat(),
                last_seen=dates[-1].isoformat(),
                next_renewal_estimate=estimate_next_date(dates[-1], cadence).isoformat(),
                transaction_count=len(rows),
                price_change_percent=round(price_change, 1),
                duplicate_cluster="",
                cancellation_url=cancel_url,
                review_flags=flags,
                source="detected",
                transactions=[asdict(row) for row in rows],
            )
        )

    manual = manual or []
    for item in manual:
        next_renewal = item.next_renewal or (date.today() + timedelta(days=30)).isoformat()
        key = normalize_merchant(item.merchant)
        category, cancel_url = catalog_for(key)
        detected.append(
            DetectedSubscription(
                merchant=item.merchant,
                merchant_key=key,
                category=item.category if item.category != "uncategorized" else category,
                cadence=item.cadence,
                confidence=0.7,
                latest_amount=round(item.amount, 2),
                average_amount=round(item.amount, 2),
                annualized_cost=round(item.amount * annual_factor(item.cadence), 2),
                currency=item.currency,
                first_seen=next_renewal,
                last_seen=next_renewal,
                next_renewal_estimate=next_renewal,
                transaction_count=1,
                price_change_percent=0.0,
                duplicate_cluster="",
                cancellation_url=cancel_url,
                review_flags=["manual_entry"],
                source="manual",
                transactions=[],
            )
        )

    duplicates_by_category = Counter(item.category for item in detected)
    for item in detected:
        if duplicates_by_category[item.category] >= 2 and item.category not in ("uncategorized", ""):
            item.duplicate_cluster = item.category
            if "possible_duplicate_category" not in item.review_flags:
                item.review_flags.append("possible_duplicate_category")

    return sorted(detected, key=lambda item: item.annualized_cost, reverse=True)


def cancellation_priority(item: DetectedSubscription, today: date) -> tuple[int, str, list[str]]:
    score = 0
    reasons = []
    next_renewal = parse_date(item.next_renewal_estimate)
    days_until = (next_renewal - today).days
    if item.annualized_cost >= 300:
        score += 25
        reasons.append("high annualized cost")
    if item.price_change_percent >= 10:
        score += 20
        reasons.append("recent price increase")
    if item.duplicate_cluster:
        score += 18
        reasons.append("similar category duplicate")
    if 0 <= days_until <= 14:
        score += 15
        reasons.append("renewal is soon")
    if item.confidence < 0.65:
        score -= 10
        reasons.append("needs review before action")
    if item.source == "manual":
        score -= 4
        reasons.append("manual entry should be verified")
    if score >= 55:
        action = "review_or_cancel_first"
    elif score >= 35:
        action = "check_usage_and_plan"
    elif score >= 20:
        action = "monitor"
    else:
        action = "keep_unless_unused"
    return max(0, score), action, reasons


def analyze_subscriptions(subscriptions: list[DetectedSubscription], today: str | None = None) -> dict:
    current = parse_date(today) if today else date.today()
    category_summary: dict[str, dict] = {}
    timeline = []
    action_queue = []
    total_annual = 0.0

    for item in subscriptions:
        total_annual += item.annualized_cost
        bucket = category_summary.setdefault(item.category, {"count": 0, "annualized_cost": 0.0, "merchants": []})
        bucket["count"] += 1
        bucket["annualized_cost"] += item.annualized_cost
        bucket["merchants"].append(item.merchant)

        priority, action, reasons = cancellation_priority(item, current)
        days_until = (parse_date(item.next_renewal_estimate) - current).days
        timeline.append(
            {
                "merchant": item.merchant,
                "next_renewal_estimate": item.next_renewal_estimate,
                "days_until": days_until,
                "amount": item.latest_amount,
                "currency": item.currency,
                "confidence": item.confidence,
                "review_flags": item.review_flags,
            }
        )
        action_queue.append(
            {
                "merchant": item.merchant,
                "priority_score": priority,
                "recommended_action": action,
                "annualized_cost": item.annualized_cost,
                "next_renewal_estimate": item.next_renewal_estimate,
                "reasons": reasons,
                "cancellation_url": item.cancellation_url,
                "confidence": item.confidence,
            }
        )

    for value in category_summary.values():
        value["annualized_cost"] = round(value["annualized_cost"], 2)

    action_queue = sorted(action_queue, key=lambda row: row["priority_score"], reverse=True)
    timeline = sorted(timeline, key=lambda row: row["days_until"])
    top_cancel = [row for row in action_queue if row["recommended_action"] in ("review_or_cancel_first", "check_usage_and_plan")]
    savings = {
        "cancel_top_1": round(sum(row["annualized_cost"] for row in top_cancel[:1]), 2),
        "cancel_top_3": round(sum(row["annualized_cost"] for row in top_cancel[:3]), 2),
        "cancel_all_duplicate_or_price_increase": round(
            sum(
                item.annualized_cost
                for item in subscriptions
                if item.duplicate_cluster or item.price_change_percent >= 10
            ),
            2,
        ),
        "cut_20_percent": round(total_annual * 0.2, 2),
    }
    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "summary": {
            "subscription_count": len(subscriptions),
            "annualized_cost": round(total_annual, 2),
            "monthly_equivalent": round(total_annual / 12, 2) if subscriptions else 0.0,
            "needs_review_count": sum(1 for item in subscriptions if item.review_flags),
            "high_priority_count": sum(1 for row in action_queue if row["priority_score"] >= 55),
        },
        "subscriptions": [asdict(item) for item in subscriptions],
        "category_summary": category_summary,
        "renewal_timeline": timeline,
        "action_queue": action_queue,
        "savings_scenarios": savings,
        "method_notes": [
            "Recurring charges are inferred from repeated merchant names and transaction cadence.",
            "The product does not connect to banks or cancel subscriptions for the user.",
            "Amounts are estimates based on imported statement data and should be reviewed before decisions.",
        ],
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Subscription Leak Radar Report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Detected subscriptions: {report['summary']['subscription_count']}",
        f"- Estimated annualized cost: ${report['summary']['annualized_cost']:.2f}",
        f"- Monthly equivalent: ${report['summary']['monthly_equivalent']:.2f}",
        f"- Items needing review: {report['summary']['needs_review_count']}",
        "",
        "## Priority Queue",
        "",
    ]
    for row in report["action_queue"]:
        lines.append(
            f"- **{row['merchant']}**: {row['recommended_action']} "
            f"(${row['annualized_cost']:.2f}/yr, score {row['priority_score']}, confidence {row['confidence']})"
        )
        if row["reasons"]:
            lines.append(f"  - Why: {', '.join(row['reasons'])}")
        if row["cancellation_url"]:
            lines.append(f"  - Cancellation/help URL: {row['cancellation_url']}")
    lines.extend(["", "## Savings Scenarios", ""])
    for key, value in report["savings_scenarios"].items():
        lines.append(f"- {key.replace('_', ' ').title()}: ${value:.2f}/yr")
    lines.extend(["", "## Method Notes", ""])
    for note in report["method_notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def save_outputs(report: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "subscription-leak-report.json"
    md_path = output_dir / "subscription-leak-report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def load_sample(path: Path) -> tuple[list[Transaction], dict]:
    return parse_csv_transactions(path.read_text(encoding="utf-8"))

