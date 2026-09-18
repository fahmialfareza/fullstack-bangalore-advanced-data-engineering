# Aturan Data

## Users
| Field | Ketentuan | Penanganan |
|---|---|---|
| `user_id` | Wajib dan unik | Trim. Nilai kosong atau duplikat menyebabkan `DROP`. |
| `name` | Teks opsional | Trim. Teks kosong menjadi `NULL`. |
| `email` | Email opsional | Trim dan lowercase. Format tidak valid menjadi `NULL`. |
| `city` | Teks opsional | Trim. Teks kosong menjadi `NULL`. |

## Products
| Field | Ketentuan | Penanganan |
|---|---|---|
| `product_id` | Wajib dan unik | Trim. Nilai kosong atau duplikat menyebabkan `DROP`. |
| `name` | Teks wajib | Trim. Nilai kosong menyebabkan `DROP`. |
| `price` | Angka wajib, nilai ≥ 0 | Konversi numeric string. Nilai tidak valid atau negatif menyebabkan `DROP`. |

## Transactions
| Field | Ketentuan | Penanganan |
|---|---|---|
| `tx_id` | Wajib dan unik | Trim. Nilai kosong atau duplikat menyebabkan `DROP`. |
| `quantity` | Bilangan bulat positif | Konversi integer string. Nilai tidak valid, nol, negatif, desimal, dan boolean menyebabkan `DROP`. |
| `user_id`, `product_id` | Referensi berbentuk teks | Trim. Validasi relasi tidak termasuk pada tahap ini. |

## Struktur decision log
Setiap entry memuat `entity`, `id`, `field`, `raw`, `action`, `clean`, dan `reason`.
