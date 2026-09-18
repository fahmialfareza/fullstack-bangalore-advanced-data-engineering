# Ringkasan Pekerjaan — Kualitas Data Operasional

## Permintaan
Siapkan data pengguna, produk, dan transaksi untuk kebutuhan pelaporan. Pertahankan record yang valid, pisahkan record yang melanggar aturan wajib, dan catat setiap perubahan material.

## Data masuk
- `data/raw/users.json`
- `data/raw/products.json`
- `data/raw/transactions.json`

File pada folder `data/raw` bersifat read-only.

## Hasil yang diserahkan
- file JSON bersih untuk setiap entitas;
- file JSON rejected beserta alasan penolakan;
- satu decision log gabungan;
- hasil validasi yang dapat dijalankan ulang.

## Prinsip keputusan
- **DROP** — record ditolak karena nilai wajib tidak valid.
- **FIX** — nilai diperbaiki dengan aturan yang deterministik.
- **NULL** — record dipertahankan, tetapi nilai opsional yang tidak valid dikosongkan.

## Kriteria penerimaan
| Entitas | Raw | Clean | Rejected |
|---|---:|---:|---:|
| Users | 16 | 14 | 2 |
| Products | 12 | 10 | 2 |
| Transactions | 15 | 12 | 3 |

Hasil diterima apabila `python validate_delivery.py` menampilkan `READY FOR REVIEW`.
