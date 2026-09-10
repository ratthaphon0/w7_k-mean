"""Canonical product mapping and strict validation for the W7 lesson."""
from __future__ import annotations

import math
from typing import Any


class ValidationError(ValueError):
    pass


def _finite_number(value: Any, field: str, *, integer: bool = False) -> float:
    if isinstance(value, bool) or value is None:
        raise ValidationError(f"{field}: expected a finite number")
    if isinstance(value, str):
        if not value.strip():
            raise ValidationError(f"{field}: blank value")
        value = value.strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field}: malformed number")
    if not math.isfinite(number):
        raise ValidationError(f"{field}: must be finite")
    if number < 0:
        raise ValidationError(f"{field}: must be non-negative")
    if integer and number != int(number):
        raise ValidationError(f"{field}: must be an integer")
    return int(number) if integer else number


def _text(value: Any, field: str, *, required: bool = False) -> str:
    if value is None:
        if required:
            raise ValidationError(f"{field}: missing")
        return ""
    text = str(value).strip()
    if required and not text:
        raise ValidationError(f"{field}: blank")
    return text


def canonicalize(row: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Map one trusted source row to the canonical, raw-normalization shape."""
    source_id = _text(source.get("source_id"), "source_id", required=True)
    product_id = _text(row.get("id"), "id", required=True)
    name_key = "name"
    desc_key = "description"
    category_key = "category"
    stock_key = "stock"
    price_key = "price"
    stock = _finite_number(row.get(stock_key), stock_key, integer=True)
    price = _finite_number(row.get(price_key), price_key)
    record = {
        "product_key": f"{source_id}:{product_id}",
        "source_id": source_id,
        "source_product_id": product_id,
        "is_mock": bool(source.get("is_mock", False)),
        "name": _text(row.get(name_key), name_key, required=True),
        "description": _text(row.get(desc_key), desc_key),
        "category": _text(row.get(category_key), category_key),
        "price": price,
        "stock": stock,
        "price_source": "api",
        "price_is_synthetic": bool(row.get("price_is_synthetic", False)),
    }
    return record


def normalize_rows(rows: list[dict[str, Any]], source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        try:
            if not isinstance(row, dict):
                raise ValidationError("row: expected object")
            record = canonicalize(row, source)
            if record["product_key"] in seen:
                raise ValidationError("duplicate product key within source")
            seen.add(record["product_key"])
            accepted.append(record)
        except ValidationError as exc:
            rejected.append({"source_id": source.get("source_id"), "row_index": index, "reason": str(exc)})
    return accepted, rejected
