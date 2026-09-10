#!/usr/bin/env python3
"""Run collection, optional K-means, and plots with explicit mode badges."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", "/tmp/w7-matplotlib-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/w7-xdg-cache")
from aggregator.app import collect
from analysis.clustering import TrainingBlocked, fit_snapshot
from analysis.plots import make_plots
from analysis.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["snapshot", "live"], default="snapshot")
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    snapshot = collect(args.mode, partial=args.partial)
    out = ROOT / "outputs" / snapshot["run_id"]
    if snapshot["training"]["blocked"]:
        print(json.dumps({"run_id": snapshot["run_id"], "mode": snapshot["mode"], "completeness": snapshot["completeness"], "training_blocked": snapshot["training"]["reason"]}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    try:
        result = fit_snapshot(snapshot, selected_k=args.k)
    except TrainingBlocked as exc:
        print(f"TRAINING_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
    (out / "clustering.result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    plots = make_plots(result, out)
    exports = write_report(result, out)
    print(json.dumps({"run_id": snapshot["run_id"], "mode": snapshot["mode"], "matrix_shape": result["matrix_shape"], "selected": result["selected"], "plots": plots, "exports": exports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
