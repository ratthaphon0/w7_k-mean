# ทำตามทีละขั้น: Three Product APIs → K-means

คู่มือนี้ใช้สำหรับเพื่อนที่ต้องการ clone project แล้วรันผลลัพธ์เดียวกันบนเครื่องตนเอง

## 1. เตรียมเครื่องมือ

ต้องมี Python 3 และ Git จากนั้น clone repository:

```sh
git clone https://github.com/ratthaphon0/w7_k-mean.git
cd w7_k-mean
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 2. ตรวจว่า API ทั้งสามแหล่งเข้าถึงได้

```sh
curl --fail 'http://119.59.102.161:3067/api/products?page=1&limit=20'
curl --fail 'http://119.59.102.161:3120/api/products?page=1&limit=20'
curl --fail 'http://119.59.102.161:3121/api/products?page=1&limit=20'
```

แต่ละคำสั่งต้องคืน JSON ที่มีรายการสินค้า, `price` และ `stock`.

## 3. ดูว่า project รู้จักแหล่งข้อมูลใดบ้าง

เปิด `sources.example.json`:

- `source_id` ระบุเจ้าของหรือที่มาของสินค้า
- `url` คือ endpoint ที่ project จะเรียก
- `adapter` ระบุรูปแบบ JSON ที่รับได้
- `is_mock` ระบุว่าชุดข้อมูลนั้นเป็นตัวอย่างหรือไม่

ห้ามแก้ URL ของแหล่งข้อมูลโดยไม่ refresh snapshot และตรวจผลใหม่

## 4. รันแบบ live

```sh
./scripts/run_demo.sh --mode live --k 3
```

โปรแกรมจะ fetch API จริง, validate ข้อมูล, สร้างเวกเตอร์ `[price, stock]`, scale ข้อมูล แล้วให้ K-means สร้าง 3 กลุ่ม

## 5. เปิดผลลัพธ์ของรอบที่เพิ่งรัน

terminal จะแสดง path ของ `outputs/<run_id>/`. เปิดไฟล์นี้ใน browser:

```sh
xdg-open outputs/<run_id>/report.html
```

ในโฟลเดอร์เดียวกันมี `collection.normalized.json`, `clustering.result.json`, `cluster-memberships.csv`, `centroids.csv` และกราฟ PNG สำหรับตรวจสอบผล

## 6. ถ้า API เข้าไม่ได้ ใช้ snapshot

```sh
./scripts/run_demo.sh --mode snapshot --k 3
```

โหมดนี้ใช้ข้อมูลที่ capture ไว้แล้วใน repository จึงไม่เรียก network ระหว่างรัน ผลยังผ่าน pipeline เดียวกัน แต่ต้องระบุว่าเป็น snapshot เมื่อแชร์ผล

## 7. เมื่อต้องเปลี่ยน API หรือข้อมูลต้นทาง

1. แก้ source ใน `sources.example.json`
2. ตรวจ JSON response ว่ามี `id`, `name`, `price`, `stock`
3. รัน `./scripts/run_demo.sh --mode live --k 3` และตรวจ report
4. เมื่อยืนยันว่า response ถูกต้อง ค่อยรัน `.venv/bin/python scripts/refresh_snapshot.py`
5. รัน test ด้วย `.venv/bin/python -m unittest discover -s tests -v`

หาก API ใหม่เป็น Supabase/Firebase ให้ดู [EXTERNAL_CLOUD_SOURCE_SETUP.md](EXTERNAL_CLOUD_SOURCE_SETUP.md) ก่อนเปลี่ยน source จริง
