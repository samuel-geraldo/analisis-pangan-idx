"""
Membangun database SQLite (pangan.db) dari 4 CSV hasil analisis, dengan
skema ternormalisasi (dim_saham + tabel fakta), lalu menjalankan contoh
query analisis dari queries.sql.

File CSV sumber (harus sudah ada di folder yang sama):
- harga_saham_pangan.csv
- return_harian_pangan.csv
- ringkasan_sektor_pangan.csv
- indikator_teknikal_pangan.csv

Output: pangan.db (database SQLite ternormalisasi, 5 tabel dasar)

Setelah pangan.db dibuat, jalankan juga:
  python analisis_statistik.py   -> mengisi tabel uji_statistik
  python regresi_kebijakan.py    -> mengisi tabel regresi_kebijakan
"""

import re
import sqlite3
import pandas as pd

DB_PATH = "pangan.db"


def _wide_ke_long(path_csv, kolom_nilai):
    """CSV harga/return disimpan wide (1 kolom per saham). Diubah ke long
    format (1 baris per saham per tanggal) supaya gampang di-query pakai SQL."""
    df_wide = pd.read_csv(path_csv, index_col=0)
    df_wide.index.name = "tanggal"
    df_long = df_wide.reset_index().melt(
        id_vars="tanggal", var_name="ticker", value_name=kolom_nilai
    )
    return df_long.dropna(subset=[kolom_nilai])


def _buat_skema(conn):
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS regresi_kebijakan;
    DROP TABLE IF EXISTS uji_statistik;
    DROP TABLE IF EXISTS ringkasan_sektor;
    DROP TABLE IF EXISTS indikator_teknikal;
    DROP TABLE IF EXISTS return_harian;
    DROP TABLE IF EXISTS harga_saham;
    DROP TABLE IF EXISTS dim_saham;

    CREATE TABLE dim_saham (
        ticker TEXT PRIMARY KEY,
        tahap_rantai_pasok TEXT
    );

    CREATE TABLE harga_saham (
        tanggal TEXT, ticker TEXT, harga REAL,
        PRIMARY KEY (tanggal, ticker),
        FOREIGN KEY (ticker) REFERENCES dim_saham(ticker)
    );

    CREATE TABLE return_harian (
        tanggal TEXT, ticker TEXT, return_harian REAL,
        PRIMARY KEY (tanggal, ticker),
        FOREIGN KEY (ticker) REFERENCES dim_saham(ticker)
    );

    CREATE TABLE indikator_teknikal (
        tanggal TEXT, ticker TEXT, ma20 REAL, ma50 REAL, rsi14 REAL,
        PRIMARY KEY (tanggal, ticker),
        FOREIGN KEY (ticker) REFERENCES dim_saham(ticker)
    );

    CREATE TABLE ringkasan_sektor (
        ticker TEXT, periode TEXT,
        rata_rata_return_harian REAL, volatilitas REAL, return_kumulatif REAL,
        PRIMARY KEY (ticker, periode),
        FOREIGN KEY (ticker) REFERENCES dim_saham(ticker)
    );
    """)
    conn.commit()


def build_database():
    conn = sqlite3.connect(DB_PATH)
    _buat_skema(conn)

    # 1. Dimensi saham: ticker -> tahap rantai pasok (sumber: ringkasan_sektor_pangan.csv,
    #    diambil unik supaya ticker cuma muncul sekali di tabel dimensi)
    ringkasan_csv = pd.read_csv("ringkasan_sektor_pangan.csv")
    dim = ringkasan_csv[["Price", "tahap_rantai_pasok"]].drop_duplicates()
    dim = dim.rename(columns={"Price": "ticker"})
    dim.to_sql("dim_saham", conn, if_exists="append", index=False)

    # 2. Harga saham (wide -> long)
    harga = _wide_ke_long("harga_saham_pangan.csv", "harga")
    harga.to_sql("harga_saham", conn, if_exists="append", index=False)

    # 3. Return harian (wide -> long)
    ret = _wide_ke_long("return_harian_pangan.csv", "return_harian")
    ret.to_sql("return_harian", conn, if_exists="append", index=False)

    # 4. Indikator teknikal (sudah long) - ambil kolom yang relevan saja,
    #    tahap_rantai_pasok tidak diikutkan karena sudah ada di dim_saham
    indikator = pd.read_csv("indikator_teknikal_pangan.csv")
    indikator = indikator.rename(columns={"MA20": "ma20", "MA50": "ma50", "RSI14": "rsi14"})
    indikator[["tanggal", "ticker", "ma20", "ma50", "rsi14"]].to_sql(
        "indikator_teknikal", conn, if_exists="append", index=False
    )

    # 5. Ringkasan sektor (sudah long) - rename kolom, tahap_rantai_pasok dibuang
    #    karena sudah ada di dim_saham
    ringkasan = ringkasan_csv.rename(columns={
        "Price": "ticker",
        "rata_rata_return_harian(%)": "rata_rata_return_harian",
        "volatilitas(%)": "volatilitas",
        "return_kumulatif(%)": "return_kumulatif",
    })
    ringkasan[["ticker", "periode", "rata_rata_return_harian", "volatilitas", "return_kumulatif"]].to_sql(
        "ringkasan_sektor", conn, if_exists="append", index=False
    )

    conn.close()
    print(f"Database '{DB_PATH}' berhasil dibuat dengan skema ternormalisasi:")
    print("  - dim_saham (ticker, tahap_rantai_pasok)")
    print("  - harga_saham (tanggal, ticker, harga)")
    print("  - return_harian (tanggal, ticker, return_harian)")
    print("  - indikator_teknikal (tanggal, ticker, ma20, ma50, rsi14)")
    print("  - ringkasan_sektor (ticker, periode, rata_rata_return_harian, volatilitas, return_kumulatif)")
    print()
    print("Lanjutkan dengan:")
    print("  python analisis_statistik.py   # isi tabel uji_statistik")
    print("  python regresi_kebijakan.py    # isi tabel regresi_kebijakan")


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
