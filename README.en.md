# Subscription Leak Radar

English | [中文](README.zh-CN.md)

Subscription Leak Radar is a local-first recurring charge audit desk for people who want to find forgotten subscriptions, price creep, duplicate services, and upcoming renewals from their own statement exports.

- Detect recurring charges from bank or credit-card CSV exports instead of asking you to hand-write every subscription.
- Estimate annualized spend, renewal timing, price increases, duplicate categories, and cancellation priority.
- Export a Markdown and JSON report you can review privately before cancelling or downgrading services.

Screenshot/GIF to be added before launch.

Quick demo:

```bash
python server.py
```

Open `http://127.0.0.1:8786`, click **Load sample**, then **Run analysis**.

## Problem

Recurring charges are easy to ignore because they are small, automatic, and scattered across cards, bank accounts, app stores, PayPal, and free trials. A person may remember the obvious subscriptions, but still miss duplicate streaming services, app-store renewals, annual charges, AI tools used once, or a plan that quietly became more expensive.

The painful part is not only the math. The real work is opening statements, finding repeated merchants, recognizing disguised billing names, estimating the annual impact, checking which renewals are soon, and deciding what to cancel first.

## Why Existing Approaches Are Not Enough

Spreadsheets work only after the user has already found and typed every subscription. Budgeting apps can be powerful, but many require account linking, cloud sync, or paid plans before the user gets a clear subscription audit. Manual subscription trackers often ask the user to enter merchant names, dates, and prices one by one, which is exactly the work the product should reduce.

Subscription Leak Radar focuses on a smaller local-first workflow: import statement-like data, infer recurring charges, surface the highest-value review items, and export a decision report.

## What This Project Does

`statement CSV or pasted transaction text -> recurring charge detection -> renewal and cost analysis -> cancellation priority queue -> Markdown/JSON report`

The app parses transactions, normalizes merchant names, groups repeated charges, infers cadence, estimates annualized cost, flags price increases and category duplicates, then ranks what to review first.

## Key Features

- Flexible CSV column mapping for common bank and card export headers such as `date`, `posted_date`, `description`, `merchant`, `amount`, `debit`, and `charge`.
- Pasted transaction text parser for statement lines copied from PDFs, emails, or banking pages.
- Manual subscription entry for items that do not appear in the imported sample window.
- Recurrence detection with cadence inference for weekly, monthly, quarterly, annual, and irregular charges.
- Price-change detection when the latest charge is meaningfully higher than the first observed charge.
- Duplicate category flags for overlapping services such as multiple AI tools, streaming services, storage plans, or app-store subscriptions.
- Renewal timeline, category spend board, cancellation priority queue, and what-if savings scenarios.
- Local Markdown and JSON export.

## Why this is useful

This turns a messy card or bank statement into a subscription leak map: repeated merchants, estimated billing cadence, price changes, duplicate categories, renewal timing, and the cancellation queue that deserves review first.

## Demo / Screenshots

Screenshot/GIF to be added before launch.

The bundled demo data includes 40+ realistic statement rows across streaming, AI tools, storage, app-store billing, gym membership, annual membership, and one-time non-subscription purchases.

## Quick Start

```bash
cd products/product-020/repo
python server.py
```

Then open:

```text
http://127.0.0.1:8786
```

No internet connection, account linking, API key, or external service is required.

## Example Input / Output

Sample CSV:

```csv
Date,Description,Amount,Currency,Account
2026-03-05,NETFLIX.COM 866-579-7172,-17.99,USD,Checking
2026-04-04,NETFLIX.COM 866-579-7172,-17.99,USD,Checking
2026-03-15,OPENAI CHATGPT SUBSCRIPTION,-20.00,USD,Credit Card
2026-04-15,OPENAI CHATGPT SUBSCRIPTION,-20.00,USD,Credit Card
```

Output files:

```text
outputs/subscription-leak-report.md
outputs/subscription-leak-report.json
```

Example output summary:

```text
Detected subscriptions: 11
Estimated annualized cost: $2,800+
Priority queue: Adobe, gym membership, AI-tool duplicates, Netflix price increase
Savings scenarios: cancel top 1, cancel top 3, cancel duplicate/price-increase items, cut 20%
```

## Use Cases

- Run a quarterly personal subscription audit from a credit-card export.
- Find recurring AI/software tools that were useful once but no longer justify monthly renewal.
- Identify duplicate services in the same category before budgeting.
- Review upcoming renewals before annual or monthly charges hit.
- Create a local cancellation checklist without sharing bank credentials.

## How It Works

The analyzer uses deterministic local logic. It maps flexible CSV headers into a normalized transaction model, parses pasted text lines with conservative date/amount patterns, normalizes merchant names, groups transactions by merchant key, calculates interval patterns, infers cadence, and estimates annualized cost. It then scores cancellation priority using cost, renewal timing, price changes, duplicate category signals, confidence, and review flags.

The output is intentionally decision-oriented: the app does not only say that a subscription exists; it tells the user which items deserve attention first and why.

## Project Structure

```text
subscription_leak_radar/analyzer.py  Core parser, recurrence detector, scoring, exports
server.py                           Local HTTP server
web/                                Browser UI
samples/                            Realistic sample statement export
examples/                           Pasted transaction text example
tests/                              Unit tests
scripts/smoke_test.py               User-perspective smoke test
```

## Roadmap

- Source-specific import presets for PayPal, Apple, Google Play, bank exports, and card statements.
- PDF statement text extraction helper.
- User-editable merchant catalog and cancellation URL table.
- Calendar export for upcoming renewals.
- Optional encrypted local history for month-over-month audits.

## Limitations

Subscription Leak Radar does not connect to banks, cancel services, send emails, or provide financial advice. Recurrence detection is based on imported transaction data, so short date ranges, renamed merchants, annual charges with only one observed transaction, or bundled app-store charges may need manual review. PDF/image OCR is not implemented; users can paste extracted statement text instead.

## License

MIT

## Language

中文版本: [README.zh-CN.md](README.zh-CN.md)
