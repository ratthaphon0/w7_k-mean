"""Explicit HTTP adapters for the trusted W7 source contracts."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import requests

MAX_RESPONSE_BYTES = 1_000_000

class SourceFetchError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def _safe_error(exc: Exception) -> str:
    message = str(exc).replace("\n", " ").strip()
    return message[:240] or exc.__class__.__name__


def _get_json(session: requests.Session, url: str, timeout: float) -> tuple[Any, int]:
    try:
        response = session.get(url, timeout=(timeout, timeout), headers={"Accept": "application/json"})
    except requests.RequestException as exc:
        raise SourceFetchError(_safe_error(exc)) from exc
    if response.status_code >= 400:
        raise SourceFetchError(f"HTTP {response.status_code}", status=response.status_code)
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise SourceFetchError("response exceeds 5 MB limit")
    try:
        return response.json(), response.status_code
    except ValueError as exc:
        raise SourceFetchError("response is not valid JSON", status=response.status_code) from exc


def _page_meta(payload: dict[str, Any]) -> tuple[int, int | None, int | None]:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise SourceFetchError("data/meta response has invalid meta")
    try:
        page = int(meta.get("page", 1))
    except (TypeError, ValueError):
        raise SourceFetchError("pagination page is invalid")
    total = meta.get("total")
    total_pages = meta.get("totalPages", meta.get("total_pages"))
    try:
        total = int(total) if total is not None else None
        total_pages = int(total_pages) if total_pages is not None else None
    except (TypeError, ValueError):
        raise SourceFetchError("pagination totals are invalid")
    return page, total, total_pages


def fetch_source(source: dict[str, Any], *, timeout: float = 8.0, session: requests.Session | None = None) -> dict[str, Any]:
    """Fetch all rows under a configured adapter with bounded pagination."""
    own_session = session is None
    session = session or requests.Session()
    adapter = source["adapter"]
    url = source["url"]
    rows: list[dict[str, Any]] = []
    pages = 0
    seen_keys: set[str] = set()
    total: int | None = None
    try:
        if adapter in {"appashif_data_meta", "data_meta"}:
            page = 1
            while True:
                page_url = url + ("&" if "?" in url else "?") + f"page={page}&limit=100"
                payload, status = _get_json(session, page_url, timeout)
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise SourceFetchError("data/meta adapter expected object with data array", status=status)
                current_page, current_total, total_pages = _page_meta(payload)
                if current_page != page:
                    raise SourceFetchError("pagination page did not advance as requested")
                page_rows = payload["data"]
                page_keys = [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in page_rows]
                digest = hashlib.sha256("\n".join(page_keys).encode()).hexdigest()
                if digest in seen_keys:
                    raise SourceFetchError("repeated pagination page detected")
                seen_keys.add(digest)
                rows.extend(page_rows)
                pages += 1
                total = current_total if current_total is not None else total
                if len(rows) > 5000:
                    raise SourceFetchError("row limit exceeded")
                done = (total_pages is not None and page >= total_pages) or not page_rows
                if done:
                    if total is not None and len(rows) != total:
                        raise SourceFetchError(f"pagination total mismatch: received {len(rows)}, expected {total}")
                    break
                page += 1
                if pages >= 100:
                    raise SourceFetchError("page limit exceeded")
        else:
            raise SourceFetchError(f"unsupported adapter: {adapter}")
        return {"status": 200, "rows": rows, "pages": pages, "fetched": len(rows), "total": total}
    finally:
        if own_session:
            session.close()


def fetch_with_retry(source: dict[str, Any], *, timeout: float = 8.0) -> dict[str, Any]:
    last: SourceFetchError | None = None
    for attempt in range(2):
        try:
            return fetch_source(source, timeout=timeout)
        except SourceFetchError as exc:
            last = exc
            if exc.status is not None and exc.status in {401, 403, 404}:
                break
            if attempt == 0:
                time.sleep(0.15)
    assert last is not None
    raise last
