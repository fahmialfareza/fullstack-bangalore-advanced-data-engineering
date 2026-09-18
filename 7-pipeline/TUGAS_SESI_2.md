# Tugas Sesi 2 — Pipeline Tokobangalore

Semua angka di bawah dapat dibuat ulang dengan menjalankan `01_buat_data.py` sampai `06_data_telat.py` secara berurutan dari folder ini.

## 1. Mengubah batas tunggu

Lima batas tunggu pada `06_data_telat.py` diubah menjadi 1, 10, 20, 30, dan 60 menit. Hasilnya:

| Batas tunggu | Transaksi hilang | Penjualan tercatat | Selisih dari total |
| -----------: | ---------------: | -----------------: | -----------------: |
|      1 menit |              239 |     Rp 543.089.950 |      Rp 85.649.750 |
|     10 menit |              159 |     Rp 575.906.150 |      Rp 52.833.550 |
|     20 menit |               86 |     Rp 601.177.000 |      Rp 27.562.700 |
|     30 menit |               37 |     Rp 615.252.850 |      Rp 13.486.850 |
|     60 menit |                0 |     Rp 628.739.700 |               Rp 0 |

Saya memilih batas tunggu **30 menit** untuk dashboard penjualan harian. Pilihan ini sudah mencatat 97,9% dari total penjualan, sedangkan data yang belum masuk hanya 37 dari 1.671 transaksi non-batal (2,2%), senilai Rp 13.486.850. Menunggu sampai 60 menit memang memberi angka lengkap, tetapi dashboard menjadi 30 menit lebih lambat. Angka 30 menit dapat ditampilkan sebagai angka sementara lalu direkonsiliasi kembali setelah seluruh data masuk. Untuk kebutuhan mendesak seperti deteksi penipuan, saya akan memilih batas yang lebih pendek karena kecepatan tindakan lebih penting.

## 2. Menambah aturan harga tidak wajar

Aturan baru di `03_silver.py` menolak order jika:

```sql
harga_satuan > 10 * harga_normal
```

Harga normal berasal dari `dim_products`. Order yang gagal tidak dibuang diam-diam, tetapi masuk ke `data_ditolak` dengan alasan
`harga_satuan lebih dari 10x harga normal`. `01_buat_data.py` membuat satu fixture deterministik, `T02000`, dengan harga 11 kali harga katalog. Test `test_harga_tidak_wajar_ditolak` membuktikan tiga hal: input memang melewati batas, order tidak masuk ke Silver, dan alasan penolakannya tersimpan. Hasil pipeline menunjukkan tepat satu order ditolak oleh aturan ini.

## 3. Menambah tabel Gold per status

Tabel baru bernama `gold_per_status`. `nilai_order` memperlihatkan nilai semua order, sedangkan `penjualan` dan `laba` hanya diakui untuk status yang tidak `batal`. Dengan begitu, nilai pembatalan tetap terlihat tanpa menganggapnya sebagai pendapatan.

```sql
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
ORDER BY jumlah_order DESC;
```

Hasilnya:

| Status | Jumlah order |  Unit |    Nilai order |      Penjualan |           Laba | Persen order |
| ------ | -----------: | ----: | -------------: | -------------: | -------------: | -----------: |
| bayar  |        1.173 | 1.619 | Rp 436.260.750 | Rp 436.260.750 | Rp 110.749.750 |        61,4% |
| kirim  |          498 |   688 | Rp 192.478.950 | Rp 192.478.950 |  Rp 48.484.950 |        26,1% |
| batal  |          238 |   335 |  Rp 85.692.550 |           Rp 0 |           Rp 0 |        12,5% |

Total `penjualan` dari tabel ini adalah Rp 628.739.700 dan sudah diperiksa agar sama dengan total pada `gold_kategori`, `gold_per_jam`, `gold_produk`, serta perhitungan langsung dari `silver_orders`.
