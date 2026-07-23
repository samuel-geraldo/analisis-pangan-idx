"""
Membangun database SQLite dari CSV hasil analisis, lalu menjalankan
contoh query analisis dari queries.sql.

File CSV sumber (harus sudah ada di folder yang sama):
- harga_saham_pangan.csv
- return_harian_pangan.csv
- ringkasan_sektor_pangan.csv
- indikator_teknikal_pangan.csv

Output: pangan_idx.db (database SQLite berisi 4 tabel)
"""

import re
import sqlite3
import pandas as pd

DB_PATH = "pangan_idx.db"


def _wide_ke_long(path_csv, kolom_nilai):
    """CSV harga/return disimpan wide (1 kolom per saham). Diubah ke long
    format (1 baris per saham per tanggal) supaya gampang di-query pakai SQL."""
    df_wide = pd.read_csv(path_csv, index_col=0)
    df_wide.index.name = "tanggal"
    df_long = df_wide.reset_index().melt(
        id_vars="tanggal", var_name="ticker", value_name=kolom_nilai
    )
    return df_long.dropna(subset=[kolom_nilai])


def build_database():
    conn = sqlite3.connect(DB_PATH)

    # 1. Harga saham (wide -> long)
    harga = _wide_ke_long("harga_saham_pangan.csv", "harga")
    harga.to_sql("harga_saham", conn, if_exists="replace", index=False)

    # 2. Return harian (wide -> long)
    ret = _wide_ke_long("return_harian_pangan.csv", "return_harian")
    ret.to_sql("return_harian", conn, if_exists="replace", index=False)

    # 3. Ringkasan sektor (sudah long) - rename kolom biar gampang dipakai di SQL
    ringkasan = pd.read_csv("ringkasan_sektor_pangan.csv")
    ringkasan = ringkasan.rename(columns={
        "Price": "ticker",
        "rata_rata_return_harian(%)": "avg_return_harian",
        "volatilitas(%)": "volatilitas",
        "return_kumulatif(%)": "return_kumulatif",
    })
    ringkasan.to_sql("ringkasan_sektor", conn, if_exists="replace", index=False)

    # 4. Indikator teknikal (sudah long) - rename kolom jadi lowercase
    indikator = pd.read_csv("indikator_teknikal_pangan.csv")
    indikator = indikator.rename(columns={"MA20": "ma20", "MA50": "ma50", "RSI14": "rsi14"})
    indikator.to_sql("indikator_teknikal", conn, if_exists="replace", index=False)

    conn.close()
    print(f"Database '{DB_PATH}' berhasil dibuat dengan 4 tabel:")
    print("  - harga_saham (tanggal, ticker, harga)")
    print("  - return_harian (tanggal, ticker, return_harian)")
    print("  - ringkasan_sektor (ticker, avg_return_harian, volatilitas, return_kumulatif, tahap_rantai_pasok, periode)")
    print("  - indikator_teknikal (tanggal, ticker, harga, ma20, ma50, rsi14, tahap_rantai_pasok)")


def jalankan_semua_query(path_sql="queries.sql"):
    """Baca queries.sql, pisahkan tiap query berdasarkan header '-- QUERY N: ...',
    jalankan satu-satu, dan cetak hasilnya dalam bentuk tabel."""
    conn = sqlite3.connect(DB_PATH)
    with open(path_sql, "r", encoding="utf-8") as f:
        isi = f.read()

    # tiap query diawali komentar '-- QUERY <nomor>: <judul>' dan diakhiri ';'
    pola = re.compile(r"-- QUERY (\d+): (.+?)\n(.*?);", re.DOTALL)
    for nomor, judul, query in pola.findall(isi):
        print(f"\n{'=' * 70}")
        print(f"QUERY {nomor}: {judul.strip()}")
        print("=" * 70)
        try:
            hasil = pd.read_sql_query(query, conn)
            print(hasil.to_string(index=False))
        except Exception as e:
            print(f"[Error menjalankan query] {e}")

    conn.close()


if __name__ == "__main__":
    build_database()
    jalankan_semua_query()
