"""
Tujuh pemeriksaan supaya kita tidak cuma percaya bahwa pipeline-nya benar.

Jalankan dulu 01 sampai 04, baru:  python -m pytest test_pipeline.py -v
"""

import sqlite3

import pytest


@pytest.fixture
def db():
    koneksi = sqlite3.connect("tokobangalore.db")
    yield koneksi
    koneksi.close()


def satu(db, sql):
    return db.execute(sql).fetchone()[0]


def test_tidak_ada_order_id_ganda(db):
    """Satu order_id cuma boleh muncul sekali. Kalau dobel, penjualan ikut dobel."""
    baris = satu(db, "SELECT COUNT(*) FROM silver_orders")
    unik = satu(db, "SELECT COUNT(DISTINCT order_id) FROM silver_orders")
    assert baris == unik


def test_status_sudah_seragam(db):
    """Setelah dibersihkan hanya boleh ada tiga status, semuanya huruf kecil."""
    status = [r[0] for r in db.execute("SELECT DISTINCT status FROM silver_orders")]
    assert sorted(status) == ["batal", "bayar", "kirim"]


def test_semua_baris_silver_lolos_aturan(db):
    """Tidak boleh ada jumlah nol, customer kosong, atau produk di luar katalog."""
    assert satu(db, "SELECT COUNT(*) FROM silver_orders WHERE jumlah <= 0") == 0
    assert satu(db, "SELECT COUNT(*) FROM silver_orders WHERE customer_id = ''") == 0
    assert satu(db, "SELECT COUNT(*) FROM silver_orders WHERE kategori IS NULL") == 0


def test_harga_tidak_wajar_ditolak(db):
    """Fixture T02000 memang >10x harga normal, lalu ditolak oleh Silver."""
    harga_satuan, harga_normal = db.execute(
        """SELECT CAST(b.harga_satuan AS INTEGER), p.harga
           FROM bronze_orders b
           JOIN dim_products p ON p.product_id = b.product_id
           WHERE b.order_id = 'T02000'"""
    ).fetchone()

    assert harga_satuan > 10 * harga_normal  # test tidak boleh lolos secara kosong
    assert satu(db, "SELECT COUNT(*) FROM silver_orders WHERE order_id = 'T02000'") == 0
    assert satu(
        db,
        "SELECT COUNT(*) FROM silver_orders "
        "WHERE harga_satuan > 10 * harga_normal",
    ) == 0
    assert db.execute(
        "SELECT alasan FROM data_ditolak WHERE order_id = 'T02000'"
    ).fetchone()[0] == "harga_satuan lebih dari 10x harga normal"


def test_yang_ditolak_disimpan_bukan_dibuang(db):
    """Setiap baris yang gagal harus punya catatan alasannya."""
    assert satu(db, "SELECT COUNT(*) FROM data_ditolak") > 0
    assert satu(db, "SELECT COUNT(*) FROM data_ditolak WHERE alasan IS NULL") == 0


def test_kolom_turunan_dihitung_benar(db):
    """total harus sama dengan jumlah x harga_satuan, tanpa kecuali."""
    salah = satu(db, "SELECT COUNT(*) FROM silver_orders "
                     "WHERE total <> jumlah * harga_satuan")
    assert salah == 0


def test_empat_tabel_gold_totalnya_sama(db):
    """Dipotong dari empat sudut pandang, totalnya harus sama."""
    kategori = satu(db, "SELECT SUM(penjualan) FROM gold_kategori")
    per_jam = satu(db, "SELECT SUM(penjualan) FROM gold_per_jam")
    produk = satu(db, "SELECT SUM(penjualan) FROM gold_produk")
    status = satu(db, "SELECT SUM(penjualan) FROM gold_per_status")
    manual = satu(db, "SELECT SUM(total) FROM silver_orders WHERE status <> 'batal'")
    assert kategori == per_jam == produk == status == manual
