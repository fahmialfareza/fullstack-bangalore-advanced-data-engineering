# Spark Optimization Report

## Masalah dan tujuan
Data sintetis 10,000 transaksi tersimpan dalam 32 file kecil. Kita menguji apakah pemadatan menjadi 2 file mengurangi waktu pembacaan tanpa mengubah isi data.

## Lingkungan dan cara mengulang
Python 3.12.14; Spark 4.0.1; Java 17.0.12; local[2]. Heap maksimum JVM: 1,073,741,824 byte.
Notebook utama bagian 17–20, atau dari sesi16: `python lab/spark_storage_lab.py --rows 10000 --repeats 3`.
Gunakan interpreter environment lab. Run baru menyimpan folder terpisah. Folder many adalah sumber; compact adalah hasil baru.

## Hipotesis dan variabel kontrol
File lebih sedikit dapat mengurangi biaya membuka file. Data, schema, codec Parquet, query, perangkat, dan versi Spark tetap sama. AQE mati. Hanya susunan file masukan yang dibandingkan dalam benchmark baca.
Satu warm-up per varian, kemudian 3 trial per varian dengan urutan bergantian. Median dan rentang ditampilkan. Timer baca mencakup pembuatan reader/schema dan action agregasi; penulisan serta compaction diukur terpisah.
Cache Spark tidak digunakan. Cache sistem operasi tidak dikosongkan, jadi ini pengukuran pembacaan setelah pemanasan.

## Hasil pembacaan dan penggunaan resource
| Metrik | 32 file | 2 file |
|---|---:|---:|
| Median detik | 0.2707 | 0.2534 |
| Minimum detik | 0.2475 | 0.2039 |
| Maksimum detik | 0.2720 | 0.3011 |
| Median CPU task (detik) | 0.1094 | 0.0312 |
| Median jumlah task | 4 | 4 |
| Median puncak memori operasi satu task (byte) | 0 | 0 |
| Median spill ke disk (byte) | 0 | 0 |
| File data | 32 | 2 |
| Total ukuran Parquet (byte) | 90420 | 51760 |
| Rata-rata ukuran file (byte) | 2826 | 25880 |

Speedup: 1.068 kali. Perubahan durasi: 6.38% lebih singkat; nilai negatif berarti lebih lama.
CPU task menjumlahkan waktu CPU thread task; bukan persentase CPU seluruh mesin. Puncak memori adalah maksimum peakExecutionMemory task, bukan total RAM proses. Nilai nol tidak berarti Spark tidak memakai RAM. Spill disk adalah penulisan perantara, bukan ukuran file Parquet.

## Biaya pemadatan dan simulasi biaya uang
Pemadatan sekali: 0.9709 detik (satu observasi, bukan median). Jumlah baca agar penghematan waktu menutup pemadatan: 57.
Tarif contoh Rp5,000/jam untuk mesin yang sama; ini asumsi latihan, bukan tarif layanan. Estimasi = durasi/3600 × tarif. Baca baseline Rp0.3759; kandidat Rp0.3520; pemadatan Rp1.3485.
Perhitungan ini mengabaikan waktu idle, startup, pembulatan tagihan, storage, dan jaringan. Jika mesin tetap menyala, durasi lebih singkat belum tentu mengurangi tagihan. Kapasitas CPU/RAM lebih besar perlu benchmark baru dengan tarifnya sendiri.

## Percobaan spill
Window menghitung total seluruh id sambil mempertahankan 10000 baris. Kedua varian memakai ambang in-memory 128 baris. Ambang spill dibandingkan: 2147483647 dan 512 baris.
| Varian | Median detik | Median spill disk (byte) | Hasil benar |
|---|---:|---:|---|
| normal_buffer | 0.1228 | 0 | True |
| forced_spill | 0.2391 | 52374 | True |
Konfigurasi internal ini khusus demonstrasi Spark 4.0.1. Spill sengaja dipicu; bukan bukti laptop kekurangan RAM. Tidak ada pengujian kehabisan memori. Pengaturan lama dipulihkan sesudah eksperimen.

## Pemeriksaan hasil dan kegagalan
File many dan compact dibandingkan menggunakan exceptAll dua arah: isi serta jumlah duplikat harus sama. Jumlah transaksi, jumlah order_id, dan total amount juga dibandingkan dengan rumus Python. Hasil window diperiksa satu per satu.
Pada notebook utama bagian 15, satu wilayah sengaja dihilangkan dan assertion menangkap hasil yang salah. Pada modul ini, metrik hilang, task gagal, hasil berubah, atau spill demo tidak muncul akan menghentikan run; tidak diganti dengan angka nol.

## Keputusan
Kandidat dua file lebih cepat pada median run lokal ini. Uji ulang pada data representatif sebelum dipakai.
Keputusan mempertimbangkan durasi, CPU task, ukuran file, biaya pemadatan, dan frekuensi baca. Dua file hanya parameter kelas; jangan memadatkan semua data produksi menjadi satu atau dua file.

## Batas pengujian dan eksperimen berikutnya
Data kecil pada satu mesin, tanpa jaringan MinIO, contention antar-pengguna, atau cluster terdistribusi. Tidak mengukur RAM total maupun biaya cloud aktual. Urutan bergantian mengurangi bias tetapi tidak menghilangkan pengaruh cache OS dan JVM.
Ulangi pada 300.000 baris, lalu volume yang mewakili pipeline. Bandingkan beberapa ukuran file dengan partisi tanggal yang sama. Periksa skew, puncak memori task, spill, dan median/rentang. Catat juga biaya compaction dan berapa kali data dibaca.

## Penerapan pada capstone
Pada pipeline transaksi ke lake, simpan kandidat hasil pemadatan pada lokasi baru. Periksa schema, duplikasi, jumlah transaksi, dan total penjualan per tanggal sebelum mengganti input job downstream. Bandingkan waktu end-to-end termasuk penulisan. Jika hasil berubah atau SLA memburuk, gunakan kembali lokasi sumber. Latihan ini tidak mengganti data lake sungguhan.

## Bukti yang dapat diperiksa
`environment.json`, `resource_comparison.json`, `spill/result.json`, `small_files/result.json`, plan teks, serta JSON stage/task per action. JSON warmup terpisah dari trial; ringkasan hanya memakai trial.

## Referensi
- https://spark.apache.org/docs/4.0.1/monitoring.html
- https://spark.apache.org/docs/4.0.1/sql-performance-tuning.html
- https://github.com/apache/spark/blob/v4.0.1/sql/catalyst/src/main/scala/org/apache/spark/sql/internal/SQLConf.scala
