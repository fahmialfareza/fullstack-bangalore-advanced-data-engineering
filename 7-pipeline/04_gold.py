"""
Langkah 4 — Hitung angka yang dibaca bisnis. Ini zona GOLD.

Empat tabel, empat pertanyaan yang berbeda:

  gold_kategori       kategori mana yang paling untung?
  gold_per_jam        jam berapa toko paling ramai?
  gold_produk         produk mana yang paling laku, dan seberapa dominan?
  gold_per_status     berapa nilai order dan penjualan di setiap status?

Yang batal tidak dihitung sebagai penjualan.

Di sini kita mulai pakai window function (SUM OVER, RANK OVER). Bedanya
dengan GROUP BY biasa: hasilnya tetap satu baris per kelompok, tapi bisa
melihat baris lain untuk menghitung kumulatif dan peringkat.

Jalankan:  python 04_gold.py
"""

import sqlite3

db = sqlite3.connect("tokobangalore.db")

db.executescript("""
DROP TABLE IF EXISTS gold_kategori;
DROP TABLE IF EXISTS gold_per_jam;
DROP TABLE IF EXISTS gold_produk;
DROP TABLE IF EXISTS gold_per_status;
""")

# =========================================================================
# 1. Ringkasan per kategori, lengkap dengan margin dan kontribusi
# =========================================================================
db.execute("""
CREATE TABLE gold_kategori AS
SELECT
    kategori,
    COUNT(*)                                  AS jumlah_order,
    SUM(jumlah)                               AS unit_terjual,
    SUM(total)                                AS penjualan,
    SUM(laba)                                 AS laba,
    ROUND(100.0 * SUM(laba) / SUM(total), 1)  AS margin_persen,
    ROUND(AVG(diskon_persen), 1)              AS rata_diskon,
    -- kontribusi terhadap penjualan seluruh toko
    ROUND(100.0 * SUM(total) / SUM(SUM(total)) OVER (), 1) AS kontribusi_persen
FROM silver_orders
WHERE status <> 'batal'
GROUP BY kategori
ORDER BY penjualan DESC
""")

# =========================================================================
# 2. Penjualan per jam, dengan total berjalan
# =========================================================================
db.execute("""
CREATE TABLE gold_per_jam AS
SELECT
    jam,
    COUNT(*)     AS jumlah_order,
    SUM(total)   AS penjualan,
    -- total berjalan dari jam paling pagi sampai jam ini
    SUM(SUM(total)) OVER (ORDER BY jam) AS penjualan_kumulatif
FROM silver_orders
WHERE status <> 'batal'
GROUP BY jam
ORDER BY jam
""")

# =========================================================================
# 3. Peringkat produk
# =========================================================================
db.execute("""
CREATE TABLE gold_produk AS
SELECT
    RANK() OVER (ORDER BY SUM(o.total) DESC) AS peringkat,
    p.nama,
    p.kategori,
    SUM(o.jumlah) AS unit_terjual,
    SUM(o.total)  AS penjualan,
    SUM(o.laba)   AS laba
FROM silver_orders o
JOIN dim_products p ON p.product_id = o.product_id
WHERE o.status <> 'batal'
GROUP BY p.product_id, p.nama, p.kategori
ORDER BY peringkat
""")

# =========================================================================
# 4. Ringkasan per status
#
# nilai_order menunjukkan nilai semua order, termasuk yang batal.
# penjualan dan laba hanya diakui untuk order yang tidak batal.
# =========================================================================
db.execute("""
CREATE TABLE gold_per_status AS
SELECT
    status,
    COUNT(*)                                                   AS jumlah_order,
    SUM(jumlah)                                                AS unit,
    SUM(total)                                                 AS nilai_order,
    SUM(CASE WHEN status <> 'batal' THEN total ELSE 0 END)     AS penjualan,
    SUM(CASE WHEN status <> 'batal' THEN laba ELSE 0 END)      AS laba,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)         AS persen_order
FROM silver_orders
GROUP BY status
ORDER BY jumlah_order DESC
""")

db.commit()

for tabel in ("gold_kategori", "gold_per_jam", "gold_produk", "gold_per_status"):
    n = db.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]
    print(f"  {tabel:16s} {n:>3} baris")

# Pemeriksaan cepat: total dari empat sudut pandang harus sama.
a = db.execute("SELECT SUM(penjualan) FROM gold_kategori").fetchone()[0]
b = db.execute("SELECT SUM(penjualan) FROM gold_per_jam").fetchone()[0]
c = db.execute("SELECT SUM(penjualan) FROM gold_produk").fetchone()[0]
d = db.execute("SELECT SUM(penjualan) FROM gold_per_status").fetchone()[0]
assert a == b == c == d, "total dari empat tabel gold harus sama"
print(f"\n  Total dari empat tabel cocok: Rp {a:,}")

db.close()
