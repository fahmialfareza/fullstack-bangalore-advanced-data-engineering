"""
Langkah 2 — Masukkan CSV ke database, apa adanya. Ini zona BRONZE.

Aturan bronze cuma satu: JANGAN diubah apa pun. Simpan persis seperti
yang dikirim sumber. Kalau nanti ada sengketa angka, tabel inilah buktinya.

Jalankan:  python 02_bronze.py
"""

import csv
import sqlite3
from pathlib import Path

DB = "tokobangalore.db"
DATA = Path("data")

db = sqlite3.connect(DB)

# --- buat tabel bronze ----------------------------------------------------
db.executescript("""
DROP TABLE IF EXISTS bronze_orders;
CREATE TABLE bronze_orders (
    order_id     TEXT,
    customer_id  TEXT,
    product_id   TEXT,
    jumlah       TEXT,      -- sengaja TEXT: bronze menerima apa adanya
    harga_satuan TEXT,
    status       TEXT,
    waktu_beli   TEXT,
    waktu_masuk  TEXT
);

DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    product_id  TEXT PRIMARY KEY,
    nama        TEXT,
    kategori    TEXT,
    harga       INTEGER,
    harga_modal INTEGER
);

DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
    customer_id TEXT PRIMARY KEY,
    kota        TEXT
);
""")


def muat(nama_file, tabel, jumlah_kolom):
    with (DATA / nama_file).open(encoding="utf-8") as f:
        pembaca = csv.reader(f)
        next(pembaca)                                   # lewati baris header
        baris = list(pembaca)
    tanda_tanya = ",".join("?" * jumlah_kolom)
    db.executemany(f"INSERT INTO {tabel} VALUES ({tanda_tanya})", baris)
    db.commit()
    print(f"  {tabel:16s} {len(baris):>5} baris masuk")


muat("orders.csv", "bronze_orders", 8)
muat("products.csv", "dim_products", 5)
muat("customers.csv", "dim_customers", 2)

db.close()
print(f"\nSelesai. Buka {DB} pakai DBeaver kalau mau lihat isinya.")
