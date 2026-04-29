from __future__ import annotations

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from subscription_leak_radar.analyzer import (
    ManualSubscription,
    analyze_subscriptions,
    detect_subscriptions,
    load_sample,
    parse_csv_transactions,
    parse_text_transactions,
    save_outputs,
)


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
SAMPLES = ROOT / "samples"
OUTPUTS = ROOT / "outputs"
PORT = 8786


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self.serve_file(WEB / "index.html", "text/html")
        if parsed.path == "/app.js":
            return self.serve_file(WEB / "app.js", "application/javascript")
        if parsed.path == "/styles.css":
            return self.serve_file(WEB / "styles.css", "text/css")
        if parsed.path == "/api/sample":
            transactions, metadata = load_sample(SAMPLES / "sample_transactions_90_days.csv")
            return self.json_response({"transactions": [asdict(item) for item in transactions], "metadata": metadata})
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body or "{}")
            if parsed.path == "/api/parse-csv":
                transactions, metadata = parse_csv_transactions(payload.get("csv", ""))
                return self.json_response({"transactions": [asdict(item) for item in transactions], "metadata": metadata})
            if parsed.path == "/api/parse-text":
                transactions, metadata = parse_text_transactions(payload.get("text", ""))
                return self.json_response({"transactions": [asdict(item) for item in transactions], "metadata": metadata})
            if parsed.path == "/api/analyze":
                transactions = payload.get("transactions", [])
                manual_payload = payload.get("manual_subscriptions", [])
                manual = [ManualSubscription(**item) for item in manual_payload]
                detected = detect_subscriptions_from_payload(transactions, manual)
                report = analyze_subscriptions(detected, today=payload.get("today") or "2026-04-29")
                report["saved_outputs"] = save_outputs(report, OUTPUTS)
                return self.json_response(report)
        except Exception as exc:
            return self.json_response({"error": str(exc)}, status=400)
        self.send_error(404)

    def serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def json_response(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def detect_subscriptions_from_payload(transactions_payload: list[dict], manual: list[ManualSubscription]):
    from subscription_leak_radar.analyzer import Transaction

    transactions = [Transaction(**item) for item in transactions_payload]
    return detect_subscriptions(transactions, manual)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Subscription Leak Radar running at http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()

