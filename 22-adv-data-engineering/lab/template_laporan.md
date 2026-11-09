# Laporan latihan Spark

Nama:
Tanggal:
Eksperimen:

## Lingkungan dan data

Catat versi Spark, Java, Python, jumlah core, RAM, mode eksekusi, jumlah baris, dan kondisi data. Lampirkan environment.json.

## Dugaan awal

Gejala apa yang terlihat? Apa penyebab yang diduga? Bukti apa yang akan mendukung atau membatalkan dugaan tersebut?

## Rancangan pengujian

Tuliskan baseline, kandidat, variabel yang berubah, action, warm-up, jumlah pengulangan, serta batas timer.

| Varian | Konfigurasi | Run 1 | Run 2 | Run 3 | Median | Rentang | Hasil benar? |
|---|---|---|---|---|---|---|---|
| Baseline | Isi dari run | | | | | | |
| Kandidat | Isi dari run | | | | | | |

## Perubahan plan

Sebutkan operator yang berubah dan lampirkan plan sebelum serta sesudah action. Tambahkan tangkapan Spark UI bila tersedia. Metric yang tidak dikumpulkan ditulis 'tidak dikumpulkan'.

## Pemeriksaan hasil dan kegagalan

Lampirkan hasil pembandingan terhadap referensi. Jelaskan satu kesalahan yang sengaja dibuat, pemeriksaan yang menangkapnya, dan cara memperbaikinya.

## Kesimpulan

Apakah perubahan membantu pada data ini? Apa biaya atau risikonya? Sertakan satu percobaan yang tidak membantu dan batas pengujiannya. Jelaskan eksperimen berikutnya.

Speedup = median baseline / median kandidat.
Penurunan durasi (%) = (baseline - kandidat) / baseline x 100.

## Penggunaan resource dan file

| Metrik | Baseline | Kandidat | Satuan dan cakupan |
|---|---|---|---|
| Waktu CPU thread task | | | Detik; bukan persen CPU seluruh mesin |
| Puncak memori operasi task | | | Byte; bukan total RAM proses |
| Spill disk | | | Byte data perantara |
| Jumlah dan ukuran file | | | File Parquet saja; abaikan checksum dan _SUCCESS |
| Waktu compaction | | | Detik; pisahkan dari waktu baca |

Jika data dipadatkan, catat perbandingan isi dua arah, total transaksi, dan total nilainya.
Jika memakai simulasi biaya, tuliskan tarif asumsi, satuan, rumus, serta biaya yang belum
dihitung. Pisahkan asumsi harga dari hasil pengukuran.

## Penerapan pada capstone

Catat lokasi sumber dan kandidat, pemeriksaan sebelum mengganti input downstream,
batas waktu layanan, serta cara kembali ke sumber bila kandidat gagal.
Contoh yang sudah terisi tersedia di `../Contoh_Spark_Optimization_Report.md`.
