# Penugasan Kualitas Data

Tim operasional menerima tiga file JSON berisi data pengguna, produk, dan transaksi. Data tersebut belum siap digunakan karena terdapat teks yang tidak konsisten, nilai yang salah format, serta identifier yang hilang atau duplikat.

## Urutan kerja
1. Buka folder ini melalui VS Code.
2. Buka `notebooks/Data_Quality_Review.ipynb`.
3. Jalankan `python preflight.py` melalui PowerShell.
4. Lengkapi fungsi pada `src/foundations.py` dan `src/cleaners.py`.
5. Jalankan pemeriksaan kualitas, kemudian buat dan validasi output.

## Perintah akhir
```powershell
python quality_checks_python_core.py
python quality_checks_helper_contracts.py
python quality_checks_users.py
python quality_checks_full_pipeline.py
python run_pipeline.py
python validate_delivery.py
```

Pekerjaan selesai ketika validasi menampilkan `READY FOR REVIEW`.
