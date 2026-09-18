# Output Acuan

## Pemeriksaan Python dasar
```text
8/8 core cases passed
```

## Pemeriksaan fungsi bantu
```text
11/11 helper cases passed
```

## Ringkasan pipeline
```text
[OK] users: raw=16 clean=14 rejected=2
[OK] products: raw=12 clean=10 rejected=2
[OK] transactions: raw=15 clean=12 rejected=3
```

## Validasi akhir
```text
READY FOR REVIEW
```

## Contoh keputusan
- Email `U001` menjadi `rani@mail.com` (`FIX`).
- Email tidak valid pada `U003` menjadi `None` (`NULL`).
- Identifier kosong atau duplikat menyebabkan record ditolak (`DROP`).
- Numeric string dikonversi hanya apabila hasilnya tidak ambigu.
