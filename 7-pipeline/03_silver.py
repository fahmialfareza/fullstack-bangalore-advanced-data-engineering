"""
Langkah 3 — Bersihkan dan perkaya data. Ini zona SILVER.

Lima hal yang dikerjakan, urut:

  1. SERAGAMKAN   status "BAYAR " dan " Bayar" jadi "bayar"
  2. GABUNG       ambil harga normal dan harga modal dari katalog produk
  3. HITUNG       total, diskon, laba, lama telat, jam transaksi
  4. BUANG GANDA  satu order_id cuma boleh sekali
  5. TOLAK        yang benar-benar salah, termasuk harga > 10x harga normal

Perhatikan urutannya. Menyeragamkan didahulukan sebelum menolak, supaya
kita tidak membuang data yang sebenarnya baik-baik saja, cuma beda cara
menulisnya. Ini kesalahan yang sering terjadi di pipeline pemula.

Semua transformasi ditulis dalam SQL. Python cuma menjalankan perintahnya.

Jalankan:  python 03_silver.py
"""

import sqlite3

db = sqlite3.connect("tokobangalore.db")

db.executescript("""
DROP TABLE IF EXISTS silver_orders;
CREATE TABLE silver_orders (
    order_id      TEXT PRIMARY KEY,   -- kunci ini yang mencegah data dobel
    customer_id   TEXT,
    product_id    TEXT,
    kategori      TEXT,               -- hasil gabung dengan katalog produk
    jumlah        INTEGER,
    harga_satuan  INTEGER,
    harga_normal  INTEGER,            -- hasil gabung
    total         INTEGER,            -- jumlah x harga_satuan
    laba          INTEGER,            -- total dikurangi modal
    diskon_persen REAL,               -- selisih harga jual dan harga normal
    status        TEXT,               -- sudah diseragamkan
    tanggal       TEXT,               -- hasil pisah dari waktu_beli
    jam           INTEGER,
    telat_detik   INTEGER
);

DROP TABLE IF EXISTS data_ditolak;
CREATE TABLE data_ditolak (
    order_id TEXT,
    alasan   TEXT
);
""")

# =========================================================================
# Langkah 1 dan 2 disatukan dalam satu view: seragamkan lalu gabung katalog
# =========================================================================
db.executescript("""
DROP VIEW IF EXISTS orders_rapi;
CREATE VIEW orders_rapi AS
SELECT
    b.order_id,
    b.customer_id,
    b.product_id,
    LOWER(TRIM(b.status))              AS status_rapi,   -- "BAYAR " -> "bayar"
    CAST(b.jumlah AS INTEGER)          AS jumlah,
    CAST(b.harga_satuan AS INTEGER)    AS harga_satuan,
    b.waktu_beli,
    b.waktu_masuk,
    p.kategori,
    p.harga                            AS harga_normal,
    p.harga_modal
FROM bronze_orders b
LEFT JOIN dim_products p ON p.product_id = b.product_id;
""")

# =========================================================================
# Langkah 3, 4, 5: hitung kolom turunan, buang ganda, masukkan yang lolos
# =========================================================================
db.execute("""
INSERT OR IGNORE INTO silver_orders
SELECT
    order_id,
    customer_id,
    product_id,
    kategori,
    jumlah,
    harga_satuan,
    harga_normal,
    jumlah * harga_satuan                              AS total,
    jumlah * (harga_satuan - harga_modal)              AS laba,
    ROUND(100.0 * (harga_normal - harga_satuan) / harga_normal, 1) AS diskon_persen,
    status_rapi,
    DATE(waktu_beli)                                   AS tanggal,
    CAST(strftime('%H', waktu_beli) AS INTEGER)        AS jam,
    CAST(strftime('%s', waktu_masuk) - strftime('%s', waktu_beli) AS INTEGER)
FROM orders_rapi
WHERE jumlah > 0
  AND customer_id <> ''
  AND kategori IS NOT NULL                 -- produknya ada di katalog
  AND harga_satuan <= 10 * harga_normal    -- harga ekstrem dianggap salah
  AND status_rapi IN ('bayar', 'kirim', 'batal')
""")

db.execute("""
INSERT INTO data_ditolak
SELECT DISTINCT order_id,
       CASE
           WHEN jumlah <= 0        THEN 'jumlah harus lebih dari 0'
           WHEN customer_id = ''   THEN 'customer_id kosong'
           WHEN kategori IS NULL   THEN 'product_id tidak ada di katalog: ' || product_id
           WHEN harga_satuan > 10 * harga_normal
                                    THEN 'harga_satuan lebih dari 10x harga normal'
           ELSE 'status tidak dikenal: ' || status_rapi
       END
FROM orders_rapi
WHERE jumlah <= 0
   OR customer_id = ''
   OR kategori IS NULL
   OR harga_satuan > 10 * harga_normal
   OR status_rapi NOT IN ('bayar', 'kirim', 'batal')
""")

db.commit()

# --- laporan singkat ------------------------------------------------------
def satu(sql):
    return db.execute(sql).fetchone()[0]

bronze = satu("SELECT COUNT(*) FROM bronze_orders")
unik = satu("SELECT COUNT(DISTINCT order_id) FROM bronze_orders")
tolak = satu("SELECT COUNT(*) FROM data_ditolak")
silver = satu("SELECT COUNT(*) FROM silver_orders")
variasi = satu("SELECT COUNT(DISTINCT status) FROM bronze_orders")

print(f"  bronze          : {bronze:>5} baris masuk")
print(f"  cara tulis status: {variasi:>4} variasi, diseragamkan jadi 3")
print(f"  kiriman ganda   : {bronze - unik:>5} baris")
print(f"  order unik      : {unik:>5} baris")
print(f"  ditolak         : {tolak:>5} baris")
print(f"  silver          : {silver:>5} baris")
print(f"\n  lolos           : {silver / unik:.1%} dari order yang unik")

assert unik - tolak == silver

print("\n  Alasan penolakan:")
for alasan, n in db.execute(
        "SELECT alasan, COUNT(*) FROM data_ditolak GROUP BY alasan ORDER BY 2 DESC"):
    print(f"    {n:>3}  {alasan}")

print("\n  Contoh baris silver yang sudah diperkaya:")
kolom = "order_id, kategori, jumlah, harga_satuan, total, laba, diskon_persen, jam"
for baris in db.execute(f"SELECT {kolom} FROM silver_orders LIMIT 3"):
    print(f"    {baris}")

db.close()
