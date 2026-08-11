"""
Membuat chart_return_kumulatif.png untuk slide deck.
Data diambil langsung dari ringkasan_sektor_pangan.csv (tidak ada angka yang di-hardcode/diestimasi).
Mengikuti Design System dari Figma (lihat komentar warna di bawah).
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

# --- Design tokens (dari Figma) ---
POSITIF = "#276B45"
NEGATIF = "#B23A32"
AKSEN_TAHAP = "#E2571F"
TEKS_SEKUNDER = "#7C726C"
TEKS_UTAMA = "#1A1614"
BG = "#FFFFFF"
GRID = "#E7E0DB"

# Font: Inter/IBM Plex Mono tidak tersedia di sistem ini -> fallback resmi sesuai instruksi
FONT_SANS = "Arial"
_mono_tersedia = any("plex mono" in f.name.lower() for f in fm.fontManager.ttflist)
FONT_MONO = "IBM Plex Mono" if _mono_tersedia else "DejaVu Sans Mono"
plt.rcParams["font.family"] = FONT_SANS

# --- Muat & cross-check data ---
df = pd.read_csv("ringkasan_sektor_pangan.csv")

urutan_ticker = ["AALI.JK", "BISI.JK", "CPIN.JK", "JPFA.JK", "ICBP.JK", "INDF.JK", "^JKSE"]
tahap_per_ticker = {
    "AALI.JK": "Hulu", "BISI.JK": "Hulu",
    "CPIN.JK": "Menengah", "JPFA.JK": "Menengah",
    "ICBP.JK": "Hilir", "INDF.JK": "Hilir",
    "^JKSE": "Benchmark",
}

verifikasi_manual = {
    "AALI.JK": (-7.96, 5.15), "CPIN.JK": (-7.91, -34.75), "INDF.JK": (18.62, -1.02),
    "ICBP.JK": (30.7, -42.6), "BISI.JK": (-2.9, -50.3), "JPFA.JK": (25.9, 48.4),
    "^JKSE": (13.27, -20.42),
}

p1_vals, p2_vals = [], []
for t in urutan_ticker:
    p1 = df[(df["Price"] == t) & (df["periode"].str.contains("Periode 1"))]["return_kumulatif(%)"].iloc[0]
    p2 = df[(df["Price"] == t) & (df["periode"].str.contains("Periode 2"))]["return_kumulatif(%)"].iloc[0]
    v1, v2 = verifikasi_manual[t]
    if abs(p1 - v1) > 0.06 or abs(p2 - v2) > 0.06:
        raise SystemExit(f"MISMATCH pada {t}: CSV=({p1:.3f}, {p2:.3f}) vs verifikasi=({v1}, {v2}) -- STOP.")
    p1_vals.append(p1)
    p2_vals.append(p2)

# --- Posisi x: grouped per tahap rantai pasok dengan jarak antar-grup ---
gap_dalam_grup = 1.0
gap_antar_grup = 1.3
x_pos = []
cur = 0.0
prev_tahap = None
for t in urutan_ticker:
    tahap = tahap_per_ticker[t]
    if prev_tahap is not None and tahap != prev_tahap:
        cur += gap_antar_grup
    elif prev_tahap is not None:
        cur += gap_dalam_grup
    x_pos.append(cur)
    prev_tahap = tahap

lebar_bar = 0.36

def fmt_id(v):
    """Format Indonesia: koma sbg desimal, tanda +/- eksplisit."""
    tanda = "+" if v > 0 else ("-" if v < 0 else "")
    return f"{tanda}{abs(v):.2f}".replace(".", ",") + "%"

def spasi_huruf(s, n=1):
    """Simulasi letter-spacing di matplotlib (tidak didukung native)."""
    pad = " " * n
    return pad.join(list(s))

# --- Gambar ---
fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

for x, v1, v2 in zip(x_pos, p1_vals, p2_vals):
    warna1 = POSITIF if v1 >= 0 else NEGATIF
    warna2 = POSITIF if v2 >= 0 else NEGATIF
    b1 = ax.bar(x - lebar_bar / 2 - 0.02, v1, width=lebar_bar, color=warna1, edgecolor="none")
    b2 = ax.bar(x + lebar_bar / 2 + 0.02, v2, width=lebar_bar, color=warna2, edgecolor=BG,
                hatch="///", linewidth=0.6)
    # label nilai di ujung bar
    for bar, v, warna in [(b1[0], v1, warna1), (b2[0], v2, warna2)]:
        offset = 1.3 if v >= 0 else -1.3
        va = "bottom" if v >= 0 else "top"
        ax.text(bar.get_x() + bar.get_width() / 2, v + offset, fmt_id(v),
                 ha="center", va=va, fontsize=10.5, color=warna, fontfamily=FONT_MONO, fontweight="bold")

# baseline (garis nol) - sedikit lebih tebal dari grid
ax.axhline(0, color=TEKS_UTAMA, linewidth=1.4, zorder=3)

# grid horizontal halus
ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
ax.set_xticks([])
ax.yaxis.set_major_formatter(lambda y, _: f"{int(y)}%")
ax.tick_params(axis="y", colors=TEKS_SEKUNDER, labelsize=9.5)
for lbl in ax.get_yticklabels():
    lbl.set_fontfamily(FONT_MONO)

# padding vertikal biar label muat
ymin, ymax = min(p1_vals + p2_vals), max(p1_vals + p2_vals)
ax.set_ylim(ymin - 8, ymax + 8)

trans = ax.get_xaxis_transform()

# label P1 / P2 kecil di bawah tiap bar
for x in x_pos:
    ax.text(x - lebar_bar / 2 - 0.02, -0.035, "P1", ha="center", va="top", fontsize=8,
             color=TEKS_SEKUNDER, fontfamily=FONT_MONO, transform=trans)
    ax.text(x + lebar_bar / 2 + 0.02, -0.035, "P2", ha="center", va="top", fontsize=8,
             color=TEKS_SEKUNDER, fontfamily=FONT_MONO, transform=trans)

# label ticker (kode, monospace)
for x, t in zip(x_pos, urutan_ticker):
    ax.text(x, -0.085, t, ha="center", va="top", fontsize=11.5,
             color=TEKS_UTAMA, fontfamily=FONT_MONO, fontweight="bold", transform=trans)

# label tahap rantai pasok (aksen oranye, uppercase, letter-spacing)
grup_ticker = {"Hulu": [], "Menengah": [], "Hilir": [], "Benchmark": []}
for x, t in zip(x_pos, urutan_ticker):
    grup_ticker[tahap_per_ticker[t]].append(x)

for tahap, xs in grup_ticker.items():
    x_tengah = sum(xs) / len(xs)
    ax.text(x_tengah, -0.14, spasi_huruf(tahap.upper(), 1), ha="center", va="top",
             fontsize=10, color=AKSEN_TAHAP, fontfamily=FONT_SANS, fontweight="bold", transform=trans)

# divider tipis antar grup tahap
batas = []
prev_tahap = None
for x, t in zip(x_pos, urutan_ticker):
    tahap = tahap_per_ticker[t]
    if prev_tahap is not None and tahap != prev_tahap:
        batas.append((x_prev + x) / 2)
    prev_tahap = tahap
    x_prev = x
for bx in batas:
    ax.axvline(bx, color=GRID, linewidth=1.0, linestyle=(0, (3, 3)), zorder=1)

ax.set_xlim(x_pos[0] - 0.9, x_pos[-1] + 0.9)

# legend kecil P1 vs P2 (pola membedakan periode, warna tetap netral abu2)
legend_elemen = [
    Patch(facecolor="#9A938E", edgecolor="none", label="Periode 1"),
    Patch(facecolor="#9A938E", edgecolor="#5A544F", hatch="///", label="Periode 2", linewidth=0.6),
]
leg = ax.legend(handles=legend_elemen, loc="upper right", frameon=False, fontsize=9.5,
                 labelcolor=TEKS_SEKUNDER, handlelength=1.6, handleheight=1.4)

plt.subplots_adjust(bottom=0.22, top=0.97, left=0.06, right=0.98)
plt.savefig("chart_return_kumulatif.png", dpi=300, facecolor=BG)
plt.close()
print("FONT_MONO dipakai:", FONT_MONO)
print("Selesai: chart_return_kumulatif.png")
