"""
Langkah 5 — Lihat hasilnya.

Ini bagian "serve". Di dunia nyata yang membaca tabel gold adalah
Power BI, Metabase, atau API. Hari ini cukup dicetak ke layar.

Jalankan:  python 05_lihat_hasil.py
"""

import sqlite3

db = sqlite3.connect("tokobangalore.db")


def tampilkan(judul, sql, format_baris):
    print(f"\n{judul}")
    print("-" * 74)
    for baris in db.execute(sql):
        print(format_baris(baris))


tampilkan(
    "PER KATEGORI                 order    penjualan        laba  margin  kontribusi",
    """SELECT kategori, jumlah_order, penjualan, laba, margin_persen, kontribusi_persen
       FROM gold_kategori""",
    lambda b: f"  {b[0]:12s} {b[1]:>16,} {b[2]:>12,} {b[3]:>11,} {b[4]:>6.1f}% {b[5]:>10.1f}%",
)

tampilkan(
    "PER JAM                      order    penjualan            total berjalan",
    "SELECT jam, jumlah_order, penjualan, penjualan_kumulatif FROM gold_per_jam",
    lambda b: f"  jam {b[0]:02d}:00 {b[1]:>16,} {b[2]:>12,} {b[3]:>24,}",
)

tampilkan(
    "5 PRODUK TERATAS             unit     penjualan        laba",
    "SELECT peringkat, nama, unit_terjual, penjualan, laba FROM gold_produk LIMIT 5",
    lambda b: f"  {b[0]:>2}. {b[1]:22s} {b[2]:>5} {b[3]:>13,} {b[4]:>11,}",
)

tampilkan(
    "PER STATUS                   order    nilai order    penjualan        laba",
    """SELECT status, jumlah_order, nilai_order, penjualan, laba
       FROM gold_per_status""",
    lambda b: f"  {b[0]:12s} {b[1]:>16,} {b[2]:>12,} {b[3]:>12,} {b[4]:>11,}",
)

tampilkan(
    "ALASAN DATA DITOLAK",
    "SELECT alasan, COUNT(*) FROM data_ditolak GROUP BY alasan ORDER BY 2 DESC",
    lambda b: f"  {b[0]:56s} {b[1]:>4} baris",
)

penjualan, laba = db.execute(
    "SELECT SUM(penjualan), SUM(laba) FROM gold_kategori"
).fetchone()
print(f"\n{'=' * 74}")
print(f"  TOTAL PENJUALAN  Rp {penjualan:>13,}")
print(f"  TOTAL LABA       Rp {laba:>13,}   margin {100 * laba / penjualan:.1f}%")
print("=" * 74)

db.close()
