from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggregator.app import collect
from aggregator.validation import normalize_rows
from analysis.clustering import TrainingBlocked, fit_snapshot
from cloud_api.server import load_fixture


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.sources = json.loads((ROOT / "sources.example.json").read_text())
        self.demo = next(s for s in self.sources["sources"] if s["source_id"] == "demo-shop-b")
        data = json.loads((ROOT / "data/cloud-products.allowlisted.json").read_text())
        self.demo_rows = next(s["products"] for s in data["sources"] if s["source_id"] == "demo-shop-b")

    def test_cloud_demo_mapping_keeps_api_price_and_synthetic_flag(self):
        accepted, rejected = normalize_rows(self.demo_rows, self.demo)
        self.assertEqual(len(accepted), 4)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(accepted[0]["price"], 450)
        self.assertEqual(accepted[0]["price_source"], "api")
        self.assertTrue(accepted[0]["price_is_synthetic"])

    def test_invalid_stock_is_quarantined(self):
        accepted, rejected = normalize_rows([{"id": "x", "name": "x", "price": 10, "stock": -1}], self.sources["sources"][0])
        self.assertEqual(accepted, [])
        self.assertIn("non-negative", rejected[0]["reason"])

    def test_missing_api_price_is_quarantined(self):
        accepted, rejected = normalize_rows([{"id": "x", "name": "x", "stock": 1}], self.sources["sources"][0])
        self.assertEqual(accepted, [])
        self.assertIn("price", rejected[0]["reason"])

    def test_same_id_different_source_stays_distinct(self):
        a, _ = normalize_rows([{"id": "same", "name": "A", "price": 10, "stock": 1}], self.sources["sources"][0])
        b, _ = normalize_rows([{"id": "same", "name": "B", "price": 10, "stock": 1}], self.sources["sources"][2])
        self.assertNotEqual(a[0]["product_key"], b[0]["product_key"])

    def test_snapshot_has_three_sources_and_twelve_trainable_rows(self):
        snapshot = collect("snapshot", save=False)
        self.assertEqual(snapshot["completeness"], "complete")
        self.assertFalse(snapshot["training"]["blocked"])
        self.assertEqual(len(snapshot["sources"]), 3)
        self.assertEqual(len(snapshot["products"]), 12)
        self.assertTrue(all(p["price_source"] == "api" for p in snapshot["products"]))

    def test_cloud_fixtures_are_explicitly_synthetic(self):
        for filename in ("demo-shop-b.json", "demo-shop-c.json"):
            fixture = load_fixture(ROOT / "cloud_api" / filename)
            self.assertEqual(fixture["data_origin"], "synthetic_classroom_demo")
            self.assertEqual(len(fixture["products"]), 4)

    def test_fit_predict_is_required(self):
        products = [{"product_key": str(i), "price": float(i * 100 + 100), "stock": float(i + 1), "source_id": "x"} for i in range(6)]
        result = fit_snapshot({"run_id": "t", "mode": "SNAPSHOT", "completeness": "complete", "training": {"blocked": False}, "products": products}, selected_k=3)
        self.assertEqual(result["matrix_shape"], [6, 2])
        self.assertGreater(result["diagnostics"][0]["inertia"], 0)
        self.assertEqual(len({p["cluster"] for p in result["products"]}), 3)
        for center in result["centroids_original_units"]:
            members = [p for p in result["products"] if p["cluster"] == center["cluster"]]
            self.assertAlmostEqual(center["price_thb_per_unit"], sum(p["price"] for p in members) / len(members), places=6)

    def test_block_missing_feature(self):
        with self.assertRaises(TrainingBlocked):
            fit_snapshot({"completeness": "complete", "training": {"blocked": False}, "products": [{"product_key": "a", "price": None, "stock": 1}, {"product_key": "b", "price": 1, "stock": 2}, {"product_key": "c", "price": 2, "stock": 3}]})


if __name__ == "__main__":
    unittest.main()
