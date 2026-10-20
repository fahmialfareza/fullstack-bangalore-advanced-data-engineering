# Tugas Besar — Olist Data Platform (capstone Data Engineer Bootcamp Advanced)

Folder ini berisi tiga hal yang berbeda penerimanya:

| Folder / file | Untuk | Isi |
|---|---|---|
| `TUGAS_BESAR.md` + `docs/Tugas_Besar_Olist_Data_Platform.pdf` | **peserta** | brief tugas: konteks, dataset, 7 tahap (target, kriteria lulus, petunjuk, jebakan, pertanyaan README), bonus, rubrik, angka cek, format demo |
| `starter/` | **peserta** | stack compose (sama dengan Local Big Data Lab), `pipeline.py` kerangka (init/up/down jadi, tahap lain TODO), `scripts/check_dataset.py`, `scripts/get_dataset.py`, template DATA_CONTRACT / RUNBOOK / EVALUATION_EVIDENCE, salinan `TUGAS_BESAR.md` |
| `kunci/` + `kunci/docs/Kunci_Jawaban_Olist_Data_Platform.pdf` | **instruktur saja** | implementasi lengkap T0–T6 yang sudah dijalankan end-to-end dengan data asli, `outputs/` nyata, 47 test, dan dokumen kunci (keputusan desain, kode kunci, output, panduan menilai + angka cek tersembunyi) |
| `docs/` | pembangun dokumen | `build_pdf.py` (Markdown → PDF bergaya Fullstack Bangalore), `make_figures.py` (gambar arsitektur/tahap/event), `figures/` |

## Yang dibagikan ke peserta

Zip isi `starter/` (sudah termasuk `TUGAS_BESAR.md` dan gambar) **atau** push ke repo template GitHub. Jangan ikutkan `kunci/`.

## Menyiapkan expected output di laptopmu (sebelum kelas)

```bash
cd kunci
pip install -r requirements.txt
python scripts/get_dataset.py        # 9 CSV → data/raw
python pipeline.py init && python pipeline.py up
python pipeline.py all               # ≈ 3 menit
python pipeline.py inject all        # ≈ 5 menit
pytest tests/ -q                     # 47 passed
```

Angka yang muncul di `kunci/outputs/` adalah angka cek di `TUGAS_BESAR.md` §8.2 dan di dokumen kunci Bagian 10.2.

## Membangun ulang dokumen

```bash
python docs/make_figures.py
python docs/build_pdf.py TUGAS_BESAR.md docs/Tugas_Besar_Olist_Data_Platform.pdf --header "Tugas Besar · Olist Data Platform"
cd kunci && python docs/build_kunci.py      # KUNCI_JAWABAN.md + PDF dari template + kode + outputs/
```

Butuh `pip install markdown pygments pypdf matplotlib` dan `npm install -g playwright` (Chromium) — sama dengan modul Pertemuan 9.

## Dataset

Brazilian E-Commerce Public Dataset by Olist (Kaggle `olistbr/brazilian-ecommerce`, CC BY-NC-SA 4.0). Tidak disertakan di folder ini (126 MB);
`scripts/get_dataset.py` mengambilnya lewat Kaggle CLI atau mirror GitHub dengan isi yang identik (jumlah baris & md5 sama).
