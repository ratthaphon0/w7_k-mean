# W7: Three Cloud Product APIs → K-means

ชุดนี้เป็นตัวอย่างที่เพื่อนสามารถ clone แล้วทำตามได้ทีละขั้น โดยดึงสินค้าจาก HTTP API บน cloud 3 แหล่ง แปลงสินค้าแต่ละรายการเป็นเวกเตอร์ `[price, stock]` แล้วใช้ scikit-learn K-means จัดกลุ่ม

## Clone repository

```sh
git clone https://github.com/ratthaphon0/w7_k-mean.git
cd w7_k-mean
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

อ่านลำดับตั้งแต่ clone, ตรวจ API, รัน live และเปิดผลลัพธ์ได้ที่ [FRIEND_STEP_BY_STEP_TH.md](FRIEND_STEP_BY_STEP_TH.md)

## แหล่งข้อมูลที่ใช้

| Source | Endpoint | ข้อมูล | สถานะ |
|---|---|---|---|
| `std6730202734` (TA) | `http://119.59.102.161:3067/api/products` | สินค้าเดิม 4 รายการ | API และข้อมูลเดิม |
| `demo-shop-b` | `http://119.59.102.161:3120/api/products` | สินค้า electronics 4 รายการ | API จริงบน cloud; ข้อมูลจำลอง |
| `demo-shop-c` | `http://119.59.102.161:3121/api/products` | สินค้า study/home 4 รายการ | API จริงบน cloud; ข้อมูลจำลอง |

API ใหม่ทั้งสองมี `/health` และ `/api/products?page=1&limit=20`, ทำงานด้วย systemd และเริ่มอัตโนมัติหลัง reboot ทุก record ส่ง `price` และ `stock` จาก API โดยตรง จึงไม่ต้องใช้ไฟล์ราคาเสริม

## รัน K-means สด

เมื่อนำ ZIP ไปเครื่องอื่นและยังไม่ได้ติดตั้ง environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

```sh
cd w7_k-mean
./scripts/run_demo.sh --mode live --k 3
```

ไม่ต้อง `source .venv/bin/activate` เพราะ script ใช้ `.venv/bin/python` โดยตรง ผลจะอยู่ใน `outputs/<run_id>/`:

- `report.html` รายงานพร้อมนำเสนอ
- `price-stock-clusters.png` scatter พร้อม centroid
- `k-diagnostics.png` inertia และ silhouette
- `cluster-memberships.csv` สมาชิกแต่ละ cluster
- `centroids.csv` centroid ในหน่วยบาทและจำนวนคงเหลือ
- `collection.raw.json`, `collection.normalized.json`, `clustering.result.json` หลักฐานของ run

ตัวอย่างผล live ที่ตรวจแล้วอยู่ใน `examples/verified-live-run/` ส่วน `outputs/` ใช้เก็บผลใหม่และไม่ถูก commit ขึ้น GitHub

ผล live ที่ตรวจแล้ว:

```text
matrix = 12 x 2
k = 3
silhouette = 0.5873
cluster sizes = 3 / 4 / 5
```

## ใช้ Snapshot เมื่อ API เข้าไม่ได้

ถ้าอินเทอร์เน็ตมีปัญหา ให้รันข้อมูลที่ capture จาก API ทั้งสามไว้แล้ว:

```sh
./scripts/run_demo.sh --mode snapshot --k 3
```

ต้องการ refresh snapshot เมื่อ API เปลี่ยน:

```sh
.venv/bin/python scripts/refresh_snapshot.py
```

## ทดสอบ

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## โครงสร้างสำคัญ

```text
cloud_api/                  source code, fixtures, systemd unit, deploy/rollback
aggregator/                 HTTP adapters + validation + canonical normalization
analysis/                   StandardScaler + KMeans + plots + report
data/                       current allowlisted and normalized snapshots
scripts/run_demo.sh         one-command live/snapshot pipeline
slides/                     revised deck and speaker notes
LIVE_DEMO_RUNBOOK_TH.md     ลำดับเปิดและคำพูดสำหรับ TA
IMPLEMENTATION_HANDOFF.md   specification และ acceptance criteria
```

## การจัดกลุ่ม

K-means เรียนรู้สมาชิกจากระยะห่างของเวกเตอร์หลัง `StandardScaler`; source, category และ product ID ใช้แสดง provenance เท่านั้น ไม่ได้ใช้เป็น feature และไม่มี SQL `GROUP BY` หรือ if/else กำหนด cluster
