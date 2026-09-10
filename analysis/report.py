"""Presenter-friendly HTML and CSV exports for one recorded clustering run."""
from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Any


ROLES = {
    "std6730202734": "TA",
    "demo-shop-b": "Simulated group B",
    "demo-shop-c": "Simulated group C",
}


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "undefined"
    return f"{float(value):,.{digits}f}"


def write_report(result: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    products = sorted(result["products"], key=lambda p: (p["cluster"], p["source_id"], p["name"]))
    cluster_csv = out / "cluster-memberships.csv"
    with cluster_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cluster", "source_role", "source_id", "product_id", "name", "price_thb", "stock_units", "price_source", "price_is_synthetic", "is_mock"])
        writer.writeheader()
        for p in products:
            writer.writerow({"cluster": p["cluster"], "source_role": ROLES.get(p["source_id"], p["source_id"]), "source_id": p["source_id"], "product_id": p["source_product_id"], "name": p["name"], "price_thb": p["price"], "stock_units": p["stock"], "price_source": p.get("price_source"), "price_is_synthetic": p.get("price_is_synthetic"), "is_mock": p.get("is_mock")})
    centroid_csv = out / "centroids.csv"
    with centroid_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cluster", "price_thb_per_unit", "stock_units", "member_count"])
        writer.writeheader()
        sizes = result["selected"]["cluster_sizes"]
        for c in result["centroids_original_units"]:
            writer.writerow({**c, "member_count": sizes[str(c["cluster"])]})

    product_rows = "".join(
        f"<tr><td>C{p['cluster']}</td><td>{html.escape(ROLES.get(p['source_id'], p['source_id']))}</td>"
        f"<td><code>{html.escape(p['source_product_id'])}</code></td><td>{html.escape(p['name'])}</td>"
        f"<td>{p['price']:,.0f}</td><td>{p['stock']}</td><td>{html.escape(str(p.get('price_source')))}</td></tr>"
        for p in products
    )
    centroid_rows = "".join(
        f"<tr><td>C{c['cluster']}</td><td>{sizes[str(c['cluster'])]}</td><td>{c['price_thb_per_unit']:,.2f}</td><td>{c['stock_units']:,.2f}</td></tr>"
        for c in result["centroids_original_units"]
    )
    diagnostic_rows = "".join(
        f"<tr class={'selected' if d['k'] == result['selected']['k'] else ''}><td>{d['k']}</td><td>{d['inertia']:.4f}</td><td>{_fmt(d['silhouette'])}</td><td>{d['realized_clusters']}</td></tr>"
        for d in result["diagnostics"]
    )
    synthetic_count = sum(bool(p.get("price_is_synthetic")) for p in products)
    warning = (
        f"{synthetic_count} rows from the two simulated-group APIs are classroom data. "
        "The HTTP calls and K-means run are live; only the TA catalog is original data."
    )
    report = out / "report.html"
    report.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>W7 K-means report · {html.escape(str(result.get('run_id')))}</title>
<style>
body{{font:16px Arial,sans-serif;margin:0;background:#f5f7fa;color:#1f2937}}main{{max-width:1180px;margin:auto;padding:28px}}h1,h2{{color:#1f4e79}}.badge{{display:inline-block;padding:7px 11px;border-radius:6px;background:#1f4e79;color:white;font-weight:bold}}.warning{{background:#fff2cc;border:1px solid #d69e00;padding:14px;margin:18px 0;font-weight:bold}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card{{background:white;border:1px solid #d7dde5;border-radius:8px;padding:14px}}.value{{font-size:28px;font-weight:bold;color:#1f4e79}}section{{background:white;border:1px solid #d7dde5;border-radius:8px;padding:18px;margin:18px 0}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:8px;border-bottom:1px solid #e5e7eb;text-align:left}}th{{background:#1f4e79;color:white}}tr.selected{{background:#fff2cc;font-weight:bold}}img{{max-width:100%;height:auto;border:1px solid #d7dde5}}code{{font-family:monospace}}.note{{color:#5b6470}}@media(max-width:800px){{.cards{{grid-template-columns:1fr 1fr}}}}
</style></head><body><main>
<span class="badge">{html.escape(str(result.get('mode')))}</span>
<h1>Product K-means: price + inventory</h1>
<div class="warning">{html.escape(warning)}</div>
<div class="cards"><div class="card"><div>Matrix</div><div class="value">{result['matrix_shape'][0]} × {result['matrix_shape'][1]}</div></div><div class="card"><div>Selected k</div><div class="value">{result['selected']['k']}</div></div><div class="card"><div>Inertia</div><div class="value">{result['selected']['inertia']:.3f}</div></div><div class="card"><div>Silhouette</div><div class="value">{_fmt(result['selected']['silhouette'])}</div></div></div>
<section><h2>1. Input vectors and learned memberships</h2><p class="note">Each row is one vector [price, stock]. Source/category/ID are shown for provenance and were not model features.</p><table><thead><tr><th>Cluster</th><th>Source</th><th>Product ID</th><th>Name</th><th>Price (THB)</th><th>Stock</th><th>Price source</th></tr></thead><tbody>{product_rows}</tbody></table></section>
<section><h2>2. Price/stock scatter and centroids</h2><img src="price-stock-clusters.png" alt="K-means price and stock scatter"><p class="note">Colours are learned cluster IDs; marker shapes are API sources. C0/C1/C2 are arbitrary IDs, not ranks.</p></section>
<section><h2>3. Centroids in original units</h2><table><thead><tr><th>Cluster</th><th>Members</th><th>Mean price (THB)</th><th>Mean stock (units)</th></tr></thead><tbody>{centroid_rows}</tbody></table></section>
<section><h2>4. Candidate k diagnostics</h2><img src="k-diagnostics.png" alt="Inertia and silhouette by k"><table><thead><tr><th>k</th><th>Inertia</th><th>Silhouette</th><th>Realized clusters</th></tr></thead><tbody>{diagnostic_rows}</tbody></table><p class="note">Silhouette is an internal clustering diagnostic, not classification accuracy. Inspect membership and singleton/outlier clusters before choosing k.</p></section>
<section><h2>5. Interpretation limits</h2><p>This small snapshot demonstrates normalization, vectors, scaling and K-means. Cluster membership does not prove demand, popularity, turnover, profit or a reorder decision. Stock is inventory, not monthly sales.</p></section>
</main></body></html>""", encoding="utf-8")
    return {"report": str(report), "memberships_csv": str(cluster_csv), "centroids_csv": str(centroid_csv)}
