#!/usr/bin/env python3
"""Fetch all configured cloud APIs and replace the allowlisted teaching snapshot."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aggregator.adapters import fetch_with_retry
from aggregator.validation import normalize_rows

ALLOWED_FIELDS = (
    "id", "name", "description", "category", "price", "stock", "price_is_synthetic"
)


def main() -> None:
    cfg = json.loads((ROOT / "sources.example.json").read_text(encoding="utf-8"))
    captured = []
    normalized = []
    for source in cfg["sources"]:
        response = fetch_with_retry(source, timeout=float(cfg.get("timeout_seconds", 8)))
        accepted, rejected = normalize_rows(response["rows"], source)
        if rejected or len(accepted) != len(response["rows"]):
            raise SystemExit(f"snapshot refused for {source['source_id']}: {rejected}")
        normalized.extend(accepted)
        rows = [
            {key: row[key] for key in ALLOWED_FIELDS if key in row}
            for row in response["rows"]
        ]
        captured.append({
            "source_id": source["source_id"],
            "role": source.get("role"),
            "observed_url": source["url"],
            "http_status": response["status"],
            "adapter": source["adapter"],
            "data_origin": "synthetic_classroom_demo" if source.get("is_mock") else "ta_api",
            "products": rows,
        })
    payload = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "capture_method": "Direct HTTP GET to three cloud APIs; allowlisted product fields only",
        "sources": captured,
    }
    destination = ROOT / "data" / "cloud-products.allowlisted.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    normalized_path = ROOT / "data" / "products.normalized.snapshot.json"
    normalized_payload = {
        "mode": "snapshot",
        "captured_at": payload["captured_at"],
        "normalization": "Explicit allowlisted field mapping; no imputation; price and stock come from each API",
        "features": ["price", "stock"],
        "counts": {
            "ta": sum(p["source_id"] == "std6730202734" for p in normalized),
            "simulated": sum(p["source_id"] != "std6730202734" for p in normalized),
            "total": len(normalized),
        },
        "products": normalized,
    }
    normalized_path.write_text(json.dumps(normalized_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"snapshot": str(destination), "normalized": str(normalized_path), "sources": len(captured), "products": len(normalized)}, indent=2))


if __name__ == "__main__":
    main()
