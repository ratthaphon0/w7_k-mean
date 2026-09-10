"""Local W7 aggregator API.

Run from the bundle root with ``python -m aggregator.app``. It never accepts
arbitrary URLs from a browser; source URLs come from sources.example.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggregator.adapters import SourceFetchError, fetch_with_retry
from aggregator.validation import normalize_rows
from analysis.clustering import TrainingBlocked, fit_snapshot


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_sources() -> dict[str, Any]:
    return json.loads((ROOT / "sources.example.json").read_text(encoding="utf-8"))


def source_status(source: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"source_id": source["source_id"], "role": source.get("role"), "url_alias": source["url"], "adapter": source["adapter"], "is_mock": bool(source.get("is_mock")), **extra}


def snapshot_sources() -> list[dict[str, Any]]:
    captured = json.loads((ROOT / "data" / "cloud-products.allowlisted.json").read_text(encoding="utf-8"))
    configured = load_sources()["sources"]
    by_id = {s["source_id"]: s for s in configured}
    out = []
    for item in captured["sources"]:
        source = dict(by_id[item["source_id"]])
        source["snapshot_rows"] = item["products"]
        out.append(source)
    return out


def collect(
    mode: str = "live",
    *,
    partial: bool = False,
    save: bool = True,
) -> dict[str, Any]:
    cfg = load_sources()
    source_defs = snapshot_sources() if mode == "snapshot" else cfg["sources"]
    statuses: list[dict[str, Any]] = []
    products: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    raw_sources: list[dict[str, Any]] = []
    all_ok = True
    for source in source_defs:
        status = source_status(source, status="pending", pages_fetched=0, fetched=0, accepted=0, rejected=0)
        try:
            if mode == "snapshot":
                fetch = {"status": 200, "rows": source["snapshot_rows"], "pages": 1, "fetched": len(source["snapshot_rows"]), "total": len(source["snapshot_rows"])}
            else:
                fetch = fetch_with_retry(source, timeout=float(cfg.get("timeout_seconds", 8)))
            accepted, bad = normalize_rows(fetch["rows"], source)
            if bad:
                all_ok = False
            status.update(status="ok" if not bad else "invalid_rows", pages_fetched=fetch["pages"], fetched=fetch["fetched"], accepted=len(accepted), rejected=len(bad), total=fetch.get("total"))
            products.extend(accepted)
            rejected.extend(bad)
            raw_sources.append({"source_id": source["source_id"], "adapter": source["adapter"], "rows": fetch["rows"]})
        except (SourceFetchError, KeyError, TypeError, ValueError) as exc:
            all_ok = False
            status.update(status="error", error=str(exc)[:240])
        statuses.append(status)
    strict = bool(cfg.get("strict_sources", True)) and not partial
    completeness = "complete" if all_ok else "failed"
    if partial and not all_ok:
        completeness = "partial"
    raw_payload = {"mode": mode, "captured_at": utc_now(), "sources": raw_sources, "rejected": rejected}
    missing = [p["product_key"] for p in products if p.get("price") is None or p.get("stock") is None]
    training_error: str | None = None
    if strict and (not all_ok or missing):
        training_error = "source collection failed" if not all_ok else "missing price/stock features: " + ", ".join(missing)
    if strict and not all_ok:
        training_error = training_error or "one or more required sources failed"
    if strict and training_error:
        completeness = "blocked"
    elif partial and (not all_ok or training_error):
        completeness = "partial"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    result = {
        "run_id": run_id,
        "fetched_at": raw_payload["captured_at"],
        "mode": "PARTIAL" if partial and completeness == "partial" else mode.upper(),
        "completeness": completeness,
        "sources": statuses,
        "rejected": rejected,
        "products": products,
        "training": {"blocked": bool(training_error or (strict and not all_ok)), "reason": training_error},
    }
    if save:
        out = ROOT / "outputs" / run_id
        out.mkdir(parents=True, exist_ok=False)
        (out / "collection.raw.json").write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "collection.normalized.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "w7-aggregator"})

    @app.get("/api/combined-products")
    def combined_products():
        mode = request.args.get("mode", "live").lower()
        partial = request.args.get("partial", "false").lower() == "true"
        if mode not in {"live", "snapshot"}:
            return jsonify({"error": "mode must be live or snapshot"}), 400
        return jsonify(collect(mode, partial=partial))

    @app.get("/api/cluster")
    def cluster():
        mode = request.args.get("mode", "snapshot").lower()
        partial = request.args.get("partial", "false").lower() == "true"
        try:
            selected_k = int(request.args.get("k", "3"))
        except ValueError:
            return jsonify({"error": "k must be an integer"}), 400
        if mode not in {"live", "snapshot"}:
            return jsonify({"error": "mode must be live or snapshot"}), 400
        snapshot = collect(mode, partial=partial)
        try:
            return jsonify(fit_snapshot(snapshot, selected_k=selected_k))
        except TrainingBlocked as exc:
            return jsonify({"error": "training_blocked", "message": str(exc), "collection": snapshot}), 409

    @app.get("/")
    def index():
        return """<!doctype html><meta charset='utf-8'><title>W7 API K-means</title>
        <style>body{font:16px Arial;max-width:1100px;margin:2rem auto;color:#222}table{border-collapse:collapse;width:100%}th,td{padding:.4rem;border-bottom:1px solid #ddd;text-align:left}pre{background:#f6f6f6;padding:1rem;overflow:auto}</style>
        <h1>W7 Product clustering</h1><p>Three cloud HTTP APIs provide price and stock directly.</p>
        <button id='snapshot'>Load snapshot</button> <button id='live'>Load live cloud APIs</button><div id='out'></div>
        <script>const out=d=>{let h='<p><b>'+d.mode+'</b> / '+d.completeness+' / '+d.products.length+' rows</p><table><tr><th>source</th><th>role</th><th>status</th><th>accepted</th></tr>'+d.sources.map(s=>'<tr><td>'+s.source_id+'</td><td>'+s.role+'</td><td>'+s.status+'</td><td>'+s.accepted+'</td></tr>').join('')+'</table><h2>Products</h2><pre>'+JSON.stringify(d.products,null,2)+'</pre>';document.querySelector('#out').innerHTML=h};document.querySelector('#snapshot').onclick=async()=>out(await (await fetch('/api/combined-products?mode=snapshot')).json());document.querySelector('#live').onclick=async()=>out(await (await fetch('/api/combined-products?mode=live')).json())</script>"""

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
