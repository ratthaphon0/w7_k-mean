# Runbook นำเสนอจริง 8–10 นาที

## เตรียมก่อนเริ่ม

เปิดไว้ 5 อย่าง:

1. Browser tab: `http://119.59.102.161:3067/api/products?page=1&limit=20`
2. Browser tab: `http://119.59.102.161:3120/api/products?page=1&limit=20`
3. Browser tab: `http://119.59.102.161:3121/api/products?page=1&limit=20`
4. VS Code: `sources.example.json` และ `analysis/clustering.py`
5. Terminal ที่ directory ของ repository `w7_k-mean`

เตรียมเปิดผลที่ตรวจแล้วไว้เป็น fallback:

`examples/verified-live-run/report.html`

## ลำดับพูดและเปิดจอ

### 1. โจทย์ — 30 วินาที

พูด: “วันนี้จะดึงสินค้า 3 API มาต่อกัน สินค้าหนึ่งชิ้นกลายเป็นเวกเตอร์ `[price, stock]` แล้วให้ K-means หา cluster เอง ไม่มี SQL GROUP BY และไม่ได้ใช้ category เป็นคำตอบ”

### 2. เปิด API ทั้งสาม — 90 วินาที

เปิด tab พอร์ต 3067 ก่อน ชี้ `data`, `price`, `stock`, `meta.total=4`

เปิดพอร์ต 3120 และ 3121 ชี้ field เดียวกัน แล้วพูดให้ตรง:

“สองตัวนี้เป็น API จริงที่รันบน cloud คนละพอร์ต แต่ catalog เป็นข้อมูลจำลองสำหรับสอน จึงมี `data_origin: synthetic_classroom_demo` และ `price_is_synthetic: true`”

สรุปบนจอ: 4 + 4 + 4 = 12 products

### 3. เปิด source config — 45 วินาที

เปิด `sources.example.json` แล้วชี้ว่า aggregator รู้ URL, adapter และ provenance ของแต่ละ source จาก config ไม่รับ URL ที่ผู้ใช้ส่งเข้ามาเอง

### 4. เปิดส่วน ML — 60 วินาที

เปิด `analysis/clustering.py` แล้วชี้ 4 จุด:

- `FEATURES = ["price", "stock"]`
- `StandardScaler().fit(X)`
- `KMeans(... random_state=42, n_init=10)`
- `model.labels_` คือสมาชิกที่โมเดลเรียนรู้

พูด: “ต้อง scale เพราะราคาเป็นหลักร้อย/พัน แต่ stock เป็นหลักหน่วย/สิบ ไม่เช่นนั้นหน่วยราคาจะครอบระยะทาง”

### 5. Run code สด — 30–60 วินาที

```sh
./scripts/run_demo.sh --mode live --k 3
```

อ่านเฉพาะ:

- `mode: LIVE`
- `matrix_shape: [12, 2]`
- `k: 3`
- `silhouette: ~0.587`
- `cluster_sizes: 3 / 4 / 5`

### 6. เปิดรายงาน — 2 นาที

เปิด `outputs/<run_id>/report.html`

อธิบาย scatter:

- X = ราคาต่อหน่วย (บาท)
- Y = stock คงเหลือ
- สี = cluster ที่ K-means เรียนรู้
- รูปร่าง marker = source ใช้เพื่อดูที่มา ไม่ใช่ feature
- X ใหญ่ = centroid

อ่าน centroid:

- C0 ประมาณ 447 บาท / stock 60
- C1 ประมาณ 2,465 บาท / stock 8.75
- C2 ประมาณ 1,242 บาท / stock 29.4

ชี้ใน membership table ว่า cluster มีสินค้าจากหลาย API จึงเห็นชัดว่าโมเดลไม่ได้ group ตาม source

### 7. เปิด diagnostics — 60 วินาที

ชี้ว่า inertia ลดลงเมื่อ k เพิ่ม จึงดูอย่างเดียวไม่ได้ และใน snapshot นี้ silhouette สูงสุดที่ k=3 ประมาณ 0.587 แต่คะแนนนี้ไม่ใช่ accuracy

พูด: “ถ้าข้อมูล API เปลี่ยน ผลและ k ที่เหมาะอาจเปลี่ยน เราจึงบันทึก run และ snapshot ทุกครั้ง”

### 8. ปิด — 30 วินาที

พูด: “สิ่งที่พิสูจน์ได้คือ API aggregation, validation, vectorization และ K-means ทำงาน end-to-end สิ่งที่ยังสรุปไม่ได้คือยอดขาย ความนิยม กำไร หรือคำสั่งเติมสินค้า เพราะเรามีเพียง price กับ stock ของ snapshot เล็ก ๆ”

## ถ้า live network มีปัญหา

```sh
./scripts/run_demo.sh --mode snapshot --k 3
```

พูดให้ชัดว่าเปลี่ยนเป็น `SNAPSHOT`; algorithm เหมือนเดิม แต่ไม่ได้ fetch network ในรอบนั้น

## คำถามที่น่าจะโดนถาม

**API จริงหรือ mock?** Process, port และ HTTP request เป็นของจริงบน VPS; ข้อมูลของ demo-shop-b/c เป็น synthetic classroom data ส่วน TA source เป็น API เดิม

**ทำไม k=3?** Candidate set รอบนี้มี silhouette สูงสุดที่ k=3 และสมาชิกอ่านได้เป็นสามรูปแบบ ไม่ใช่เพราะมีสาม API

**นี่คือ query grouping หรือไม่?** ไม่ใช่ query ใช้ดึงข้อมูลเท่านั้น Membership มาจาก KMeans labels หลัง StandardScaler

**ใช้ category ช่วยไหม?** ไม่ใช้ model feature มีเพียง price และ stock; category/source ใช้แสดงที่มา

**silhouette 0.587 คือ accuracy 58.7% หรือไม่?** ไม่ใช่ ไม่มี class เฉลย เป็นคะแนนความแน่นภายในและความห่างระหว่าง cluster

**ต่อยอดอย่างไร?** เพิ่มจำนวนสินค้า เก็บ snapshot หลายวัน เพิ่มยอดขายจริง/discount/rating ที่มีนิยามเดียวกัน แล้วประเมิน feature และ k ใหม่ ห้ามเปลี่ยนชื่อ stock เป็น sales
