"""
Langkah 1 — Membuat data dummy.

Kita berpura-pura jadi "Tokobangalore", toko online kecil.
Skrip ini menulis tiga file CSV ke folder data/.

Datanya sengaja tidak rapi, meniru masalah yang benar-benar sering muncul:
  - satu order dikirim dua kali oleh sistem sumber
  - status ditulis beda-beda: "bayar", "BAYAR ", " Bayar"
  - ada order yang menunjuk produk yang tidak ada di katalog
  - jumlah nol, customer_id kosong
  - sebagian data baru sampai puluhan menit setelah transaksi

Jalankan:  python 01_buat_data.py
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)                       # supaya semua orang dapat data yang sama

DATA = Path("data")
DATA.mkdir(exist_ok=True)

# (id, nama, kategori, harga jual, harga modal)
PRODUK = [
    ("P01", "Kopi Bubuk 200g", "grocery", 32000, 21000),
    ("P02", "Beras Premium 5kg", "grocery", 78000, 64000),
    ("P03", "Minyak Goreng 2L", "grocery", 38000, 32000),
    ("P04", "Susu UHT 1L", "grocery", 21000, 16000),
    ("P05", "Kaos Polos Katun", "fashion", 75000, 32000),
    ("P06", "Kemeja Flanel", "fashion", 189000, 88000),
    ("P07", "Celana Chino", "fashion", 265000, 130000),
    ("P08", "Sepatu Sneakers", "fashion", 549000, 295000),
    ("P09", "TWS Earbuds", "elektronik", 320000, 235000),
    ("P10", "Power Bank 20000mAh", "elektronik", 285000, 210000),
    ("P11", "Keyboard Mekanik", "elektronik", 720000, 540000),
    ("P12", "SSD 1TB", "elektronik", 1250000, 1010000),
    ("P13", "Rice Cooker 1.8L", "rumah", 385000, 270000),
    ("P14", "Kipas Angin Berdiri", "rumah", 310000, 215000),
    ("P15", "Setrika Uap", "rumah", 245000, 168000),
    ("P16", "Lampu Meja LED", "rumah", 125000, 72000),
    ("P17", "Matras Yoga", "olahraga", 165000, 92000),
    ("P18", "Dumbbell 5kg", "olahraga", 195000, 140000),
    ("P19", "Botol Minum 1L", "olahraga", 89000, 48000),
    ("P20", "Raket Badminton", "olahraga", 430000, 285000),
]
KOTA = ["Jakarta", "Bandung", "Surabaya", "Medan", "Semarang", "Makassar"]

# Cara sistem sumber menulis status. Isinya sama, penulisannya beda-beda.
# Ini yang nanti kita seragamkan di langkah 3, bukan kita tolak.
TULISAN_STATUS = {
    "bayar": ["bayar", "BAYAR ", " Bayar", "Bayar"],
    "kirim": ["kirim", "KIRIM", " kirim "],
    "batal": ["batal", "Batal"],
}
BOBOT_STATUS = [("bayar", 0.62), ("kirim", 0.26), ("batal", 0.12)]
DISKON = [1.0, 1.0, 1.0, 1.0, 0.95, 0.9, 0.85, 0.75]


def undi(pasangan):
    x, batas = random.random(), 0.0
    for nilai, bobot in pasangan:
        batas += bobot
        if x <= batas:
            return nilai
    return pasangan[-1][0]


def tulis_csv(nama, header, baris):
    with (DATA / nama).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(baris)
    print(f"  {nama:16s} {len(baris):>5} baris")


# --- dimensi --------------------------------------------------------------
tulis_csv("products.csv",
          ["product_id", "nama", "kategori", "harga", "harga_modal"], PRODUK)

pelanggan = [(f"C{i:03d}", random.choice(KOTA)) for i in range(1, 101)]
tulis_csv("customers.csv", ["customer_id", "kota"], pelanggan)

# --- transaksi ------------------------------------------------------------
mulai = datetime(2026, 3, 2, 8, 0)
orders = []

for i in range(1, 2001):
    produk = random.choice(PRODUK)
    waktu_beli = mulai + timedelta(seconds=random.randint(0, 8 * 3600))

    # Berapa lama datanya baru sampai ke sistem kita.
    undian = random.random()
    if undian < 0.85:
        telat = random.randint(1, 55)          # di bawah 1 menit
    elif undian < 0.93:
        telat = random.randint(60, 900)        # 1 sampai 15 menit
    elif undian < 0.98:
        telat = random.randint(900, 1800)      # 15 sampai 30 menit
    else:
        telat = random.randint(1800, 3600)     # 30 sampai 60 menit

    status = undi(BOBOT_STATUS)
    baris = [
        f"T{i:05d}",
        random.choice(pelanggan)[0],
        produk[0],
        random.choices([1, 2, 3], [70, 22, 8])[0],
        int(produk[3] * random.choice(DISKON)),          # harga setelah diskon
        random.choice(TULISAN_STATUS[status]),           # penulisan tidak seragam
        waktu_beli.strftime("%Y-%m-%d %H:%M:%S"),
        (waktu_beli + timedelta(seconds=telat)).strftime("%Y-%m-%d %H:%M:%S"),
    ]

    # 4% data benar-benar rusak
    if random.random() < 0.04:
        rusak = random.choice(["jumlah", "customer", "produk", "status"])
        if rusak == "jumlah":
            baris[3] = 0
        elif rusak == "customer":
            baris[1] = ""
        elif rusak == "produk":
            baris[2] = "P99"          # produk ini tidak ada di katalog
        else:
            baris[5] = "pending"      # status yang memang tidak dikenal

    # Satu contoh tetap untuk tugas data quality: harga satuan 11x harga katalog.
    # Dibuat deterministik supaya aturan dan test di langkah silver selalu bisa
    # dibuktikan dengan menjalankan ulang pipeline dari awal.
    if i == 2000:
        baris[1] = "C001"
        baris[2] = "P01"
        baris[3] = 1
        baris[4] = PRODUK[0][3] * 11
        baris[5] = "bayar"

    orders.append(baris)

    # 3% dikirim ulang oleh sistem sumber
    if random.random() < 0.03:
        orders.append(list(baris))

tulis_csv("orders.csv",
          ["order_id", "customer_id", "product_id", "jumlah", "harga_satuan",
           "status", "waktu_beli", "waktu_masuk"], orders)

print("\nData siap di folder data/. Coba buka orders.csv pakai Excel.")
