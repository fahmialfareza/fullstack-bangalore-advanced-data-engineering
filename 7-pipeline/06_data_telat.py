"""
Langkah 6 — Apa yang hilang kalau kita tidak mau menunggu.

Setiap transaksi punya dua waktu:
    waktu_beli  = kapan pembeli menekan tombol bayar
    waktu_masuk = kapan datanya sampai ke sistem kita

Sebagian data datang terlambat. Kalau pipeline hanya menunggu sampai
batas tertentu lalu menutup perhitungan, transaksi yang datang setelah
batas itu tidak ikut dihitung.

Skrip ini menghitung berapa rupiah yang hilang untuk beberapa pilihan
batas tunggu.

Jalankan:  python 06_data_telat.py
"""

import sqlite3

db = sqlite3.connect("tokobangalore.db")

# Lima pilihan batas tunggu untuk tugas Sesi 2.
BATAS_TUNGGU_MENIT = (1, 10, 20, 30, 60)

total = db.execute(
    "SELECT SUM(total) FROM silver_orders WHERE status <> 'batal'"
).fetchone()[0]

print("  Total penjualan sebenarnya: Rp {:,}\n".format(total))
print("  batas tunggu   transaksi hilang   penjualan tercatat      selisih")
print("  " + "-" * 66)

for batas_menit in BATAS_TUNGGU_MENIT:
    hilang, tercatat = db.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE telat_detik > ?),
            SUM(total) FILTER (WHERE telat_detik <= ?)
        FROM silver_orders
        WHERE status <> 'batal'
        """,
        (batas_menit * 60, batas_menit * 60),
    ).fetchone()

    selisih = total - tercatat
    print(
        f"  {batas_menit:>3} menit      {hilang:>6} transaksi     "
        f"Rp {tercatat:>12,}   Rp {selisih:>10,}"
    )

print("""
  Baca tabel di atas dari kiri ke kanan.

  Makin pendek batas tunggu, makin cepat angkanya keluar, tapi makin
  banyak transaksi yang tidak terhitung. Tidak ada pilihan yang gratis.

  Pertanyaan untuk kamu: untuk dashboard penjualan harian, berapa batas
  tunggu yang kamu pilih? Lalu untuk deteksi penipuan kartu kredit,
  apakah jawabannya sama?
""")

db.close()
