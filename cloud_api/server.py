#!/usr/bin/env python3
"""Small read-only product API used by the W7 live cloud demonstration."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


class ProductApiHandler(BaseHTTPRequestHandler):
    server_version = "W7ProductAPI/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def respond(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        fixture = self.server.fixture  # type: ignore[attr-defined]
        if url.path == "/health":
            return self.respond(200, {
                "status": "ok",
                "source_id": fixture["source_id"],
                "data_origin": fixture["data_origin"],
            })
        if url.path != "/api/products":
            return self.respond(404, {"error": "not_found"})

        params = parse_qs(url.query, keep_blank_values=True)
        try:
            page = int(params.get("page", ["1"])[0])
            limit = int(params.get("limit", ["20"])[0])
            if page < 1 or not 1 <= limit <= 100:
                raise ValueError
        except ValueError:
            return self.respond(400, {"error": "page must be >= 1; limit must be 1..100"})

        rows = fixture["products"]
        offset = (page - 1) * limit
        return self.respond(200, {
            "source_id": fixture["source_id"],
            "data_origin": fixture["data_origin"],
            "currency": fixture["currency"],
            "data": rows[offset:offset + limit],
            "meta": {
                "page": page,
                "limit": limit,
                "total": len(rows),
                "totalPages": (len(rows) + limit - 1) // limit,
            },
        })


def load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"source_id", "data_origin", "currency", "products"}
    if not isinstance(payload, dict) or not required.issubset(payload):
        raise ValueError(f"invalid fixture: {path}")
    if payload["data_origin"] != "synthetic_classroom_demo":
        raise ValueError("fixture must explicitly identify synthetic classroom data")
    if not isinstance(payload["products"], list) or not payload["products"]:
        raise ValueError("fixture products must be a non-empty array")
    for row in payload["products"]:
        if not isinstance(row, dict) or not {"id", "name", "category", "price", "stock"}.issubset(row):
            raise ValueError("each product requires id, name, category, price, and stock")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--data", required=True, type=Path)
    args = parser.parse_args()
    fixture = load_fixture(args.data)
    server = ThreadingHTTPServer((args.host, args.port), ProductApiHandler)
    server.fixture = fixture  # type: ignore[attr-defined]
    print(f"{fixture['source_id']}: http://{args.host}:{args.port}/api/products", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
