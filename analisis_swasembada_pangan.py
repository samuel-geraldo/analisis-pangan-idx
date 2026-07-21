"""
Project: Dampak Kebijakan Swasembada Pangan terhadap Kinerja Saham
         Rantai Pasok Pangan di IDX

Fokus: rantai pasok pangan dari HULU (pertanian/perkebunan) -> MENENGAH
       (peternakan/pakan/protein) -> HILIR (pengolahan pangan)

Tujuan script ini:
1. Mengambil data harga saham historis dari 6 saham rantai pasok pangan + IHSG
2. Menghitung return harian & volatilitas
3. Membandingkan kinerja antar dua periode observasi (sebelum vs sesudah Okt 2024)
4. Menghitung indikator analisis teknikal: Moving Average (MA20, MA50) & RSI(14)
5. Menyimpan hasil ke file CSV yang siap dipakai di Power BI / Tableau

Catatan: indikator teknikal di sini untuk tujuan pembelajaran/portofolio analisis
data, bukan rekomendasi jual/beli saham.

Cara install library yang dibutuhkan (jalankan di terminal):
    pip install yfinance pandas
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# =========================================================
# 1. KONFIGURASI: saham rantai pasok pangan, dari hulu ke hilir
# =========================================================
saham_rantai_pasok = {
    "Hulu (Pertanian/Perkebunan)": ["AALI.JK", "BISI.JK"],
    "Menengah (Peternakan/Pakan/Protein)": ["CPIN.JK", "JPFA.JK"],
    "Hilir (Pengolahan Pangan)": ["ICBP.JK", "INDF.JK"],
}

benchmark = "^JKSE"  # Indeks Harga Saham Gabungan (IHSG)

TANGGAL_MULAI_DATA = "2023-01-01"
TANGGAL_PEMBATAS_PERIODE = "2024-10-20"  # titik pembagi periode observasi 1 & 2
TANGGAL_AKHIR = datetime.today().strftime("%Y-%m-%d")


# =========================================================
# 2. FUNGSI: ambil data harga penutupan (Close) 1 saham
# =========================================================
def ambil_data(ticker):
    print(f"Mengambil data: {ticker} ...")
    df = yf.download(ticker, start=TANGGAL_MULAI_DATA, end=TANGGAL_AKHIR, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Close"]].rename(columns={"Close": ticker})
    return df


# =========================================================
# 3. KUMPULKAN SEMUA DATA JADI SATU TABEL
# =========================================================
semua_data = []
label_tahap = {}  # mencatat saham ini masuk tahap rantai pasok mana

for tahap, tickers in saham_rantai_pasok.items():
    for t in tickers:
        semua_data.append(ambil_data(t))
        label_tahap[t] = tahap

semua_data.append(ambil_data(benchmark))
label_tahap[benchmark] = "Benchmark (IHSG)"

df_gabungan = pd.concat(semua_data, axis=1)
df_gabungan = df_gabungan.dropna(how="all")
df_gabungan = df_gabungan.ffill()  # isi tanggal libur bursa dgn harga terakhir


# =========================================================
# 4. HITUNG RETURN HARIAN (%)
# =========================================================
df_return = df_gabungan.pct_change()


# =========================================================
# 5. PISAHKAN DATA MENJADI DUA PERIODE OBSERVASI
# =========================================================
sebelum = df_return[df_return.index < TANGGAL_PEMBATAS_PERIODE]
sesudah = df_return[df_return.index >= TANGGAL_PEMBATAS_PERIODE]


def ringkas_periode(df_periode, nama_periode):
    hasil = pd.DataFrame({
        "rata_rata_return_harian(%)": df_periode.mean() * 100,
        "volatilitas(%)": df_periode.std() * 100,
        "return_kumulatif(%)": ((1 + df_periode).prod() - 1) * 100,
    })
    hasil["tahap_rantai_pasok"] = hasil.index.map(label_tahap)
    hasil["periode"] = nama_periode
    return hasil


ringkasan_sebelum = ringkas_periode(sebelum, "Periode 1 (sebelum Okt 2024)")
ringkasan_sesudah = ringkas_periode(sesudah, "Periode 2 (sesudah Okt 2024)")

ringkasan_akhir = pd.concat([ringkasan_sebelum, ringkasan_sesudah])
ringkasan_akhir = ringkasan_akhir.reset_index().rename(columns={"index": "ticker"})


# =========================================================
# 6. HITUNG INDIKATOR TEKNIKAL: MOVING AVERAGE & RSI
#    (untuk tujuan pembelajaran/portofolio, bukan rekomendasi trading)
# =========================================================
def hitung_rsi(harga, periode=14):
    """RSI (Relative Strength Index) - indikator momentum 0-100.
    Di atas 70 = overbought, di bawah 30 = oversold (aturan umum)."""
    delta = harga.diff()
    kenaikan = delta.where(delta > 0, 0.0)
    penurunan = -delta.where(delta < 0, 0.0)
    rata_kenaikan = kenaikan.rolling(window=periode).mean()
    rata_penurunan = penurunan.rolling(window=periode).mean()
    rs = rata_kenaikan / rata_penurunan
    rsi = 100 - (100 / (1 + rs))
    return rsi


daftar_indikator = []
for ticker in df_gabungan.columns:
    harga = df_gabungan[ticker]
    df_ind = pd.DataFrame({
        "tanggal": harga.index,
        "ticker": ticker,
        "harga": harga.values,
        "MA20": harga.rolling(window=20).mean().values,
        "MA50": harga.rolling(window=50).mean().values,
        "RSI14": hitung_rsi(harga, periode=14).values,
    })
    df_ind["tahap_rantai_pasok"] = label_tahap.get(ticker, "Benchmark (IHSG)")
    daftar_indikator.append(df_ind)

df_indikator = pd.concat(daftar_indikator, ignore_index=True)


# =========================================================
# 7. SIMPAN HASIL KE CSV (siap dipakai di Power BI / Tableau)
# =========================================================
df_gabungan.to_csv("harga_saham_pangan.csv")
df_return.to_csv("return_harian_pangan.csv")
ringkasan_akhir.to_csv("ringkasan_sektor_pangan.csv", index=False)
df_indikator.to_csv("indikator_teknikal_pangan.csv", index=False)

print("\nSelesai! 4 file CSV berhasil dibuat:")
print("1. harga_saham_pangan.csv           -> harga historis tiap saham")
print("2. return_harian_pangan.csv         -> return harian tiap saham")
print("3. ringkasan_sektor_pangan.csv       -> ringkasan siap dashboard")
print("4. indikator_teknikal_pangan.csv     -> MA20, MA50, RSI14 per saham per tanggal\n")
print(ringkasan_akhir)
