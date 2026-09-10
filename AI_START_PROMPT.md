# Prompt สำหรับ AI ที่รับช่วงต่อ

ทำงานใน repository `w7_k-mean` และอ่าน `README.md`, `IMPLEMENTATION_HANDOFF.md`, `LIVE_DEMO_RUNBOOK_TH.md` ก่อนแก้ไข

ระบบปัจจุบันใช้ HTTP API บน cloud 3 แหล่งเท่านั้น: TA `std6730202734` พอร์ต 3067 และ simulated classroom APIs `demo-shop-b` พอร์ต 3120 กับ `demo-shop-c` พอร์ต 3121 ทั้งสอง API ใหม่มีข้อมูล synthetic ที่ระบุ provenance ชัดเจน และทุกแหล่งส่ง `price`/`stock` จาก API โดยตรง

รักษา baseline เป็น K-means บน `[price, stock]` ด้วย StandardScaler, `random_state=42`, `n_init=10` สมาชิกต้องมาจาก KMeans labels ห้ามสร้างด้วย SQL grouping, source, category หรือ if/else threshold เก็บ source/category ไว้เพื่อ provenance เท่านั้น ห้ามเรียก stock ว่า sales/demand

คำสั่งหลักคือ `./scripts/run_demo.sh --mode live --k 3`; snapshot fallback คือ `--mode snapshot --k 3` เมื่อแก้ source contract ให้ refresh ด้วย `.venv/bin/python scripts/refresh_snapshot.py`, รัน tests, รัน live pipeline และตรวจ report/plots จริงก่อนส่งต่อ

การแก้ cloud ต้องจำกัดอยู่ใน `/opt/w7-product-apis`, `/etc/w7-product-apis`, `w7-product-api@.service` และ UFW 3120/3121 เว้นแต่ผู้ใช้อนุญาต scope ใหม่ อย่าแตะ API/database เดิมของ TA และอย่าเก็บ credentials หรือ database dumps ใน bundle
