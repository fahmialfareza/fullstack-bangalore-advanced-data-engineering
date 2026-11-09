# Menjalankan notebook Spark

Berkas utama: **Sesi_16_Spark_Optimization_Hands_On.ipynb**.

Notebook berisi definisi, kapan teknik digunakan, kode per tahap, dan cara membaca hasil.
Gunakan Python 3.10–3.13 dan Java 17. Mulai dari 10.000 baris sebelum menambah volume.

## Persiapan di Windows

Buka terminal **PowerShell** baru dari folder materi. Jalankan:

```powershell
Set-Location -LiteralPath "F:\programming\ngajar\full_stack_bangalore\sesi 17 Data Lake MinIO\sesi16"
py --version
java -version
```

Pastikan Python berada pada rentang di atas dan Java menampilkan versi 17.
Jika `.venv` belum ada, buat dengan:

```powershell
py -m venv .venv
```

Pasang paket ke environment lab:

```powershell
.\.venv\Scripts\python.exe -m pip install -r lab\requirements-notebook.txt
```

## Membuka di VS Code

1. Buka folder `sesi16` di VS Code. Gunakan ekstensi Python dan Jupyter.
2. Buka `lab/Sesi_16_Spark_Optimization_Hands_On.ipynb`.
3. Klik **Select Kernel**, lalu pilih interpreter `sesi16/.venv/Scripts/python.exe`.
4. Jalankan sel dari atas ke bawah. Gunakan **Restart Kernel**, lalu **Run All** untuk pengujian penuh dari keadaan baru.

Working directory kernel harus berada di `sesi16`, `sesi16/lab`, atau folder induk yang berisi `sesi16`.
Jika notebook melaporkan working directory tidak sesuai, buka ulang melalui folder `sesi16`.

## Alternatif: JupyterLab

Dari terminal PowerShell yang sama:

```powershell
.\.venv\Scripts\python.exe -m pip install jupyterlab
.\.venv\Scripts\python.exe -m jupyterlab --notebook-dir=lab
```

Buka notebook dari daftar file. Pilih kernel Python dari environment lab tersebut.

## Hasil yang diharapkan

- Semua sel kode selesai tanpa error yang tidak ditangani.
- Operator baseline menunjukkan `SortMergeJoin`; kandidat menunjukkan `BroadcastHashJoin`.
- Semua perbandingan hasil menghasilkan `correct=True`.
- Final plan AQE menunjukkan `isFinalPlan=true`.
- Total baris pada distribusi skew sama dengan `N_ROWS`.
- Pemeriksaan kesalahan sengaja mencetak bahwa region 0 hilang dan berhasil terdeteksi.
- Sel terakhir mencetak bahwa Spark berhenti dan environment dipulihkan.
- Folder `lab/notebook_outputs/<waktu>_<id>/verification.json` berisi `completed: true`.

Untuk melihat Spark UI, jalankan per sel dan buka alamat yang dicetak pada tahap Spark.
UI berhenti setelah sel terakhir dijalankan. Hasil plan dan pengukuran tetap tersimpan.

## Mengulang dengan data lebih besar

Ubah `N_ROWS` dari `10_000` menjadi `300_000`, kemudian restart kernel dan Run All.
Pertahankan tiga pengukuran untuk membandingkan median. Batas satu juta baris dipasang
sebagai pembatas latihan. Notebook tidak otomatis menghapus folder hasil lama.

Output yang tersimpan dalam notebook berasal dari pengujian lokal. Durasi pada perangkat
lain dapat berbeda. Notebook tidak menyimpulkan bahwa satu konfigurasi selalu paling cepat.

## Jika terjadi error

Jika Python tidak menemukan PySpark, periksa pilihan kernel terlebih dahulu. Jika Java
tidak sesuai, perbaiki PATH pada terminal lab lalu buka ulang kernel. Jika SparkContext
sudah aktif, gunakan Restart Kernel. Setelah error di tengah proses, sel penutup dapat
dipakai untuk menghentikan sesi; restart kernel juga akan menutup proses kernel tersebut.

Tidak ada operasi hapus folder, akses data MinIO, atau perubahan environment Windows
secara permanen. Notebook menulis hasil hanya ke folder run baru dan membatasi Spark UI
ke localhost. Paket perlu diunduh saat instalasi awal.


## Tambahan bagian 17–20

Notebook kini berisi 46 sel, termasuk 20 sel kode. Bagian 17 membaca metrik lokal;
18 memperlihatkan spill; 19 memadatkan Parquet; 20 membuat laporan lengkap.
Penutupan Spark dipindahkan ke bagian 21. Seluruh tahap menghasilkan 39 trial
pada REPEATS=3, selain warm-up dan pemeriksaan isi.

`spark_storage_lab.py` harus tetap berada di samping notebook. Spill dibatasi
maksimal 10.000 baris walaupun N_ROWS lebih besar. Pemadatan memakai N_ROWS.
Untuk penulisan Parquet pada Windows, pastikan dukungan Hadoop lokal sesuai.
Jika muncul error winutils atau NativeIO, gunakan Linux/Docker yang sudah disiapkan.
Paket ini tidak memasang biner Hadoop secara otomatis. Eksekusi Docker belum diuji.

Hasil tambahan berada di `storage/`: `spill/result.json`, `small_files/result.json`,
`resource_comparison.json`, dan `Spark_Optimization_Report.md`.
Disk spill forced_spill harus > 0; exact_content_equal harus True. Metrik memori
yang ditampilkan adalah memori operasi task, bukan RAM total. Tarif biaya hanya ilustrasi.
