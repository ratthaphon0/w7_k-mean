# เปลี่ยน `demo-shop-c` เป็น API จาก Supabase หรือ Firebase

เป้าหมายคือให้ `demo-shop-c` มาจาก Cloud Database ภายนอก VPS `119.59.102.161` จริง ๆ โดย database ต้องให้ read-only access สำหรับข้อมูลสินค้า และส่งอย่างน้อย `id`, `name`, `price`, `stock`.

## ทางเลือกที่แนะนำ: Supabase

1. สร้าง Supabase project และ table `products`.
2. สร้าง columns: `id` (text, primary key), `name` (text), `description` (text), `category` (text), `price` (numeric), `stock` (int8), `price_is_synthetic` (boolean). จะเก็บ `created_at` (timestamp, default `now()`) เพิ่มก็ได้.
3. Import สินค้า 4 รายการจาก `data/demo-shop-c.supabase.csv`.
4. เปิด Row Level Security และสร้าง policy ที่อนุญาตเฉพาะ `SELECT` สำหรับ `anon`; ห้ามเปิด insert, update หรือ delete.
5. ใช้ REST endpoint ของ table เช่น `https://<project-ref>.supabase.co/rest/v1/products?select=*`.
6. เก็บ Supabase anon key ไว้นอก repository แล้วให้ runtime อ่านจาก environment variable. ห้าม commit key หรือ service-role key.
7. เปลี่ยน `demo-shop-c` ใน `sources.example.json`, รัน live, ตรวจ report, แล้ว refresh snapshot.

## Firebase Realtime Database

1. สร้าง Firebase project และ Realtime Database.
2. สร้าง path `products` ที่มีสินค้าแต่ละรายการ.
3. ตั้ง rules ให้ public read ได้เฉพาะระหว่างการทดสอบ หรือใช้ token ที่ไม่ถูก commit.
4. ใช้ endpoint `https://<project>.firebaseio.com/products.json`.
5. เพิ่ม adapter สำหรับรูปแบบ object-map ของ Firebase ก่อนตั้งเป็น source จริง.

## เกณฑ์ก่อนเปลี่ยน source

- endpoint ต้องไม่ใช่ `119.59.102.161`
- response ผ่าน HTTPS
- ไม่มี key ที่ให้สิทธิ์เขียนหรือจัดการ database อยู่ใน GitHub
- K-means ยังได้รับ `price` และ `stock` จาก API โดยตรง
- live run, snapshot refresh และ unit tests ผ่านทั้งหมด
