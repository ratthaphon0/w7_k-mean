# W7 Internet Programming — AI implementation handoff

## เป้าหมาย

สาธิต end-to-end ว่าโปรแกรมสามารถดึง JSON จาก Product API บน cloud 3 แหล่ง รวม schema ที่เหมือนกันในส่วนสำคัญ แล้วส่งเวกเตอร์ตัวเลขให้ K-means เรียนรู้กลุ่มเอง โดยสมาชิก cluster ต้องมาจาก `KMeans.fit_predict`/`labels_` ไม่ใช่ SQL grouping, category, source ID หรือ threshold ที่เขียนไว้ล่วงหน้า

## Source contract ที่ล็อกแล้ว

| source_id | role | URL | records | origin |
|---|---|---|---:|---|
| `std6730202734` | TA | `http://119.59.102.161:3067/api/products` | 4 | existing TA catalog |
| `demo-shop-b` | simulated group | `http://119.59.102.161:3120/api/products` | 4 | synthetic classroom catalog |
| `demo-shop-c` | simulated group | `http://119.59.102.161:3121/api/products` | 4 | synthetic classroom catalog |

ทุก endpoint ส่ง object ที่มี `data` array และ `meta` สำหรับ pagination สอง API ใหม่ส่ง `data_origin: synthetic_classroom_demo` เพิ่มเพื่อไม่ให้สับสนว่า catalog เป็นข้อมูลธุรกิจจริง

## Architecture

```text
Cloud :3067 (TA) ----------\
Cloud :3120 (demo B) -------+--> local aggregator --> canonical records
Cloud :3121 (demo C) ------/                            |
                                                         v
                                          X = [[price, stock], ...]
                                                         |
                                              StandardScaler.fit(X)
                                                         |
                                          KMeans(k=3, random_state=42)
                                                         |
                                      labels + centroids + diagnostics
```

ไม่มี SSH tunnel ใน flow วันสอน และไม่ต้องแก้ database/API เดิมของ TA

## Canonical record

```json
{
  "product_key": "demo-shop-b:B-001",
  "source_id": "demo-shop-b",
  "source_product_id": "B-001",
  "name": "Wireless Mouse",
  "category": "Accessories",
  "price": 450.0,
  "stock": 60,
  "price_source": "api",
  "price_is_synthetic": true,
  "is_mock": true
}
```

`product_key = source_id + ':' + source_product_id` ป้องกัน ID ซ้ำข้ามร้าน ห้าม join หรือ deduplicate ด้วยชื่อสินค้า

## Validation gate

ก่อนเข้า ML ต้องตรวจ:

1. ทั้ง 3 source ตอบ HTTP สำเร็จและ pagination ไม่วนซ้ำ
2. source ละ 4 รายการ รวม 12 รายการ
3. `id`, `name`, `price`, `stock` ใช้งานได้
4. `price` และ `stock` เป็น finite non-negative number; `stock` เป็นจำนวนเต็ม
5. ไม่มี `product_key` ซ้ำภายใน source
6. strict mode block ทั้ง run หาก source ใดล่มหรือ feature หาย

raw payload เก็บไว้เฉพาะใน output ของ run ส่วน snapshot ที่อยู่ใน bundle ใช้ field allowlist เพื่อตัด image/metadata ที่ไม่เกี่ยวกับโมเดล

## ML baseline

Feature matrix:

```text
X.shape = (12, 2)
X[i] = [price_thb_per_unit, stock_units]
```

ขั้นตอน:

1. สร้าง matrix ตามลำดับ canonical records
2. fit `StandardScaler` ครั้งเดียวกับ combined snapshot
3. transform ราคาและ stock ให้อยู่ในสเกลเทียบกันได้
4. fit `KMeans(n_clusters=k, random_state=42, n_init=10)`
5. ผูก label กลับกับ record ในลำดับเดิม
6. inverse-transform centroid กลับเป็นบาทและจำนวนคงเหลือ
7. คำนวณ inertia และ silhouette สำหรับ candidate `k=2..6`

`k=3` คือ demo หลัก เพราะผลปัจจุบันแบ่งลักษณะได้อ่านง่ายและมี silhouette สูงสุดใน candidate set ของ snapshot นี้ ไม่ใช่เพราะมี 3 API

ผล live ที่ตรวจวันที่ 2026-09-10:

| cluster | members | centroid price | centroid stock | คำอธิบายเพื่ออ่านกราฟ |
|---:|---:|---:|---:|---|
| C0 | 3 | ~446.67 บาท | 60.00 | ราคาต่ำ / stock สูง |
| C1 | 4 | 2,465.00 บาท | 8.75 | ราคาสูง / stock ต่ำ |
| C2 | 5 | 1,242.00 บาท | 29.40 | ราคากลาง / stock กลาง |

เลข C0/C1/C2 เป็น label สมมติ ไม่ใช่อันดับดีหรือแย่

## Live and snapshot modes

- `--mode live`: HTTP GET สาม endpoint ทุกครั้ง แล้ว fit จาก run snapshot เดียวกัน
- `--mode snapshot`: ใช้ `data/cloud-products.allowlisted.json` สำหรับกรณี network มีปัญหา
- `--partial`: ใช้วิเคราะห์ปัญหาเท่านั้น ไม่ควรใช้เป็นผลหลักในห้อง

ทุก run สร้าง directory ใหม่เพื่อไม่ให้ผลครั้งเก่าถูกเขียนทับ

## Cloud deployment

ไฟล์ใน `cloud_api/` เป็น source of truth ของ API ใหม่:

- `/opt/w7-product-apis/server.py`
- `/opt/w7-product-apis/demo-shop-b.json`
- `/opt/w7-product-apis/demo-shop-c.json`
- `/etc/w7-product-apis/*.env`
- `/etc/systemd/system/w7-product-api@.service`
- instances `w7-product-api@demo-shop-b` และ `w7-product-api@demo-shop-c`
- UFW TCP 3120 และ 3121

Service เป็น read-only GET API, ใช้ DynamicUser, จำกัด memory/CPU/tasks, ป้องกันการเขียน system/home และ restart เมื่อ process ล้ม การ rollback อยู่ที่ `cloud_api/rollback.sh`; deployment backup อยู่ใต้ `/root/w7-product-api-backups/` บน VPS

## Acceptance criteria

- เปิด URL ทั้งสามจากเครื่องภายนอกได้และตอบ 200
- `/health` ของ 3120/3121 แสดง source ID ถูกต้อง
- source ละ 4 records พร้อม price/stock
- snapshot มี 3 sources, 12 records, 0 rejected
- K-means matrix เป็น 12×2 และมี 3 learned labels เมื่อ `k=3`
- ผล deterministic ด้วย random state เดิม
- report/plots/CSV สร้างได้
- tests ผ่าน
- bundle และสไลด์ไม่มี source รุ่นก่อน, ไฟล์ราคาเสริม หรือคำสั่งเปิด local mock server

## ข้อจำกัดที่ต้องพูด

- สินค้า 8 รายการใน demo B/C เป็น synthetic แม้ API จะรันจริงบน cloud
- 12 records เหมาะกับการอธิบาย pipeline ไม่เหมาะกับการตัดสินธุรกิจ
- stock คือ inventory snapshot ไม่ใช่ sales, demand, turnover หรือ profit
- silhouette เป็น internal clustering metric ไม่ใช่ accuracy
- ถ้าจะใช้จริงควรเพิ่มจำนวนสินค้า, snapshot หลายเวลา, feature ที่มีเหตุผล และ monitoring ของ data drift
