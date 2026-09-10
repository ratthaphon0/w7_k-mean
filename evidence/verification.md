# Verification — current live-cloud implementation

Date: 10 September 2026, Asia/Bangkok.

## Cloud checks

- root SSH succeeded on `119.59.102.161`.
- ports 3120 and 3121 were free before deployment.
- both systemd instances are enabled and active.
- listeners are owned by the new Python services on `0.0.0.0:3120` and `0.0.0.0:3121`.
- UFW rules were added for TCP 3120/3121, IPv4 and IPv6.
- pre-deployment evidence/rollback backup: `/root/w7-product-api-backups/20260909T182137Z`.
- external requests to 3067, 3120 and 3121 returned HTTP 200.
- every endpoint returned 4 products; every product had valid price and stock.
- `demo-shop-b` and `demo-shop-c` health endpoints returned their correct source IDs.
- no change was made to the TA API/database or unrelated student services.

The first deploy command reached its immediate health check before the DynamicUser services had completed startup and exited with curl status 7. Systemd then showed both services active about two seconds later. The deploy script now waits for readiness before declaring success.

## Pipeline checks

The verified command was:

```sh
./scripts/run_demo.sh --mode live --k 3
```

Result:

```text
run_id: 20260909T184721Z-73e562b8
mode: LIVE
matrix: 12 x 2
k: 3
inertia: 3.0940875676
silhouette: 0.5872799306
cluster sizes: 3 / 4 / 5
```

Candidate silhouette values were approximately k2=0.495, k3=0.587, k4=0.540, k5=0.531, k6=0.444. Therefore k=3 is a defensible choice for this fixed teaching snapshot, while remaining subject to change when the API data changes.

Centroids in original units:

- C0: 446.67 THB, stock 60.00
- C1: 2,465.00 THB, stock 8.75
- C2: 1,242.00 THB, stock 29.40

The run exported JSON, two PNG plots, HTML report, membership CSV and centroid CSV. Unit tests cover strict snapshot completeness, synthetic provenance, canonical source-qualified keys, invalid stock quarantine, missing-feature blocking, K-means labels and centroid reconstruction.

The sandbox blocks local socket binding without escalation; that earlier local PermissionError was an execution-environment restriction. External cloud HTTP and end-to-end live tests passed after authorized network execution.
