# Speaker notes

1. เปิด API 3067, 3120, 3121 ตามลำดับ และนับ 4+4+4 รายการ
2. บอกตรง ๆ ว่า demo-shop-b/c เป็นข้อมูลจำลอง แต่ HTTP API และ cloud service ทำงานจริง
3. ชี้ `price` และ `stock` ใน JSON แล้วเปิด `sources.example.json`
4. อธิบาย canonical key `source_id:product_id`; source/category ไม่เข้าโมเดล
5. เปิด `analysis/clustering.py`: matrix `[price, stock]`, StandardScaler, KMeans, labels
6. รัน `./scripts/run_demo.sh --mode live --k 3`
7. เปิด `report.html`: สีคือ learned cluster, marker คือ source, X คือ centroid
8. อ่านผล 3/4/5 สมาชิกและ centroid ประมาณ 447/60, 2465/8.75, 1242/29.4
9. ชี้ diagnostics: k=3 silhouette ประมาณ 0.587 สูงสุดใน candidate set ปัจจุบัน; ไม่ใช่ accuracy
10. ปิดด้วยข้อจำกัด: stock ไม่ใช่ sales; 12 rows และ synthetic data ใช้สอน pipeline เท่านั้น
