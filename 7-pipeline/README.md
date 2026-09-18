# Sesi 1 — Pipeline Tokobangalore

Pipeline kecil yang jalan dari awal sampai akhir: file CSV masuk ke database,
dibersihkan dan diperkaya, lalu diringkas jadi angka penjualan dan laba.

Semua transformasinya ditulis dalam SQL. Python di sini cuma menjalankan
perintahnya. Pola seperti ini yang disebut ELT.

## Yang dibutuhkan

Python 3.9 ke atas. Tidak perlu install database, SQLite sudah bawaan Python.

```bash
pip install pytest        # cuma untuk langkah pengujian
```

## Cara menjalankan

Jalankan berurutan. Tiap file mengerjakan satu hal saja.

```bash
python 01_buat_data.py      # bikin data dummy jadi 3 file CSV
python 02_bronze.py         # CSV masuk database, apa adanya
python 03_silver.py         # diseragamkan, digabung, dihitung, disaring
python 04_gold.py           # diringkas jadi angka penjualan dan laba
python 05_lihat_hasil.py    # lihat hasilnya
python 06_data_telat.py     # berapa yang hilang kalau tidak mau menunggu
python -m pytest test_pipeline.py -v
```

Hasilnya satu file `tokobangalore.db`. Buka pakai DBeaver kalau mau melihat
isinya langsung.

## Apa yang terjadi di tiap zona

**Bronze** — data masuk apa adanya, semua kolom disimpan sebagai teks. Tidak
ada yang diubah. Kalau nanti ada sengketa angka dengan tim lain, tabel ini
buktinya.

**Silver** — lima langkah, urut:

1. **Seragamkan.** Sistem sumber menulis status dengan 10 cara berbeda:
   `bayar`, `BAYAR `, ` Bayar`, `KIRIM`, dan seterusnya. Semuanya
   diseragamkan pakai `LOWER(TRIM(...))` jadi tiga nilai saja.
2. **Gabung.** `LEFT JOIN` ke `dim_products` untuk mengambil kategori, harga
   normal, dan harga modal.
3. **Hitung kolom turunan.** `total`, `laba`, `diskon_persen`, `tanggal`,
   `jam`, dan `telat_detik`.
4. **Buang kiriman ganda.** `order_id` jadi primary key, lalu
   `INSERT OR IGNORE`.
5. **Saring.** Yang benar-benar salah dipindah ke `data_ditolak` beserta
   alasannya.

Urutannya penting. Menyeragamkan didahulukan sebelum menyaring, supaya data
yang sebenarnya baik-baik saja tidak ikut terbuang cuma karena beda cara
menulis. Ini kesalahan yang sering terjadi di pipeline pemula.

**Gold** — empat tabel untuk empat pertanyaan berbeda, memakai window function
(`SUM() OVER`, `RANK() OVER`):

| Tabel | Menjawab |
| --- | --- |
| `gold_kategori` | Kategori mana yang paling untung? Termasuk margin dan kontribusi. |
| `gold_per_jam` | Jam berapa toko paling ramai? Termasuk total berjalan. |
| `gold_produk` | Produk mana yang paling laku? Termasuk peringkatnya. |
| `gold_per_status` | Berapa nilai order dan penjualan yang diakui pada tiap status? |

## Isi database

| Tabel | Zona | Isinya |
| --- | --- | --- |
| `bronze_orders` | Bronze | Apa adanya dari CSV, semua kolom masih teks |
| `silver_orders` | Silver | Bersih, seragam, sudah diperkaya 14 kolom |
| `data_ditolak` | — | Baris yang gagal, beserta alasannya |
| `gold_kategori` | Gold | Penjualan, laba, margin, kontribusi per kategori |
| `gold_per_jam` | Gold | Penjualan per jam plus total berjalan |
| `gold_produk` | Gold | Peringkat produk |
| `gold_per_status` | Gold | Nilai order dan penjualan per status |
| `dim_products` | Dimensi | 20 produk, harga jual dan harga modal |
| `dim_customers` | Dimensi | 100 pelanggan |

## Angka yang keluar (seed 42)

```
bronze           :  2053 baris masuk
cara tulis status:    10 variasi, diseragamkan jadi 3
kiriman ganda    :    53 baris
order unik       :  2000 baris
ditolak          :    91 baris
silver           :  1909 baris
lolos            : 95.5%

TOTAL PENJUALAN  Rp 628.739.700
TOTAL LABA       Rp 159.234.700   margin 25,3%
```

Seed dikunci di 42, jadi angka di laptop kamu akan sama persis dengan angka
di layar instruktur.

## Datanya sengaja tidak rapi

Di dalam `orders.csv` ada:

- **53 baris kiriman ganda** — sistem sumber mengirim ulang order yang sama
- **10 cara menulis status** — sumber tidak konsisten
- **91 baris bermasalah** — jumlah nol, `customer_id` kosong, status
  `pending` yang tidak dikenal, `product_id` `P99` yang tidak ada di
  katalog, dan satu harga satuan yang lebih dari 10 kali harga normal
- **ratusan baris telat** — datanya baru sampai 1 sampai 60 menit setelah
  transaksi

Semuanya masalah yang benar-benar muncul di pekerjaan sehari-hari.

## Yang menarik untuk didiskusikan di kelas

Jalankan `05_lihat_hasil.py`, lalu perhatikan tabel per kategori:

```
elektronik   Rp 300.384.500   margin 16,2%   kontribusi 47,8%
fashion      Rp 115.100.700   margin 45,8%   kontribusi 18,3%
```

Kategori dengan penjualan terbesar justru yang paling tipis marginnya. Angka
seperti ini tidak akan terlihat kalau pipeline hanya menjumlahkan penjualan
tanpa ikut membawa harga modal dari tabel dimensi.
