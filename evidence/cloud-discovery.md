# Current cloud topology — 10 September 2026 (Asia/Bangkok)

The user authorized root access and requested two new simulated product APIs on `119.59.102.161`, while preserving the existing TA API.

## Current sources

| source | public endpoint | response | records | price/stock |
|---|---|---|---:|---|
| `std6730202734` | `http://119.59.102.161:3067/api/products` | `{data,meta}` | 4 | present |
| `demo-shop-b` | `http://119.59.102.161:3120/api/products` | `{source_id,data_origin,data,meta}` | 4 | present |
| `demo-shop-c` | `http://119.59.102.161:3121/api/products` | `{source_id,data_origin,data,meta}` | 4 | present |

External HTTP GETs returned 200 for all three. The two new catalogs explicitly return `data_origin: synthetic_classroom_demo`; each product has `price_is_synthetic: true`. The original TA source retains its four active products and prices 890, 1,890, 1,590 and 2,190 THB.

Unrelated student services were not stopped, edited or redeployed.

## New service boundaries

- code and read-only fixtures: `/opt/w7-product-apis`
- per-instance ports: `/etc/w7-product-apis/demo-shop-{b,c}.env`
- unit: `/etc/systemd/system/w7-product-api@.service`
- enabled instances: `w7-product-api@demo-shop-b`, `w7-product-api@demo-shop-c`
- public firewall rules: TCP 3120 and 3121
- deployment backups: `/root/w7-product-api-backups/<UTC timestamp>`

The services use Python's standard-library HTTP server, allow GET only, run as DynamicUser, use read-only system/home protection, and have CPU, memory, task and file-descriptor limits.

## Data boundary

`data/cloud-products.allowlisted.json` is a direct HTTP capture with product fields needed by the lesson. Image URLs and unrelated TA metadata are omitted from this bundle. `data/products.normalized.snapshot.json` contains 12 canonical records with source-qualified keys.

Stock is inventory at one point in time. It is not monthly sales, demand, popularity, turnover or profit.
