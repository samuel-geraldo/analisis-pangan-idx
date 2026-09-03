import sqlite3
import pandas as pd
from scipy import stats
import numpy as np

conn = sqlite3.connect('pangan.db')
return_df = pd.read_sql("SELECT * FROM return_harian", conn)
return_df['tanggal'] = pd.to_datetime(return_df['tanggal'])

TANGGAL_KEBIJAKAN = '2024-10-20'
hasil = []

for ticker in return_df['ticker'].unique():
    sub = return_df[return_df['ticker'] == ticker]
    p1 = sub[sub['tanggal'] < TANGGAL_KEBIJAKAN]['return_harian']
    p2 = sub[sub['tanggal'] >= TANGGAL_KEBIJAKAN]['return_harian']

    t_stat, p_value = stats.ttest_ind(p1, p2, equal_var=False, nan_policy='omit')
    kesimpulan = "H0 gagal ditolak" if p_value > 0.05 else "H0 ditolak"

    sharpe = (p2.mean() / p2.std()) * np.sqrt(252) if p2.std() > 0 else None

    hasil.append({
        'ticker': ticker,
        'p_value': round(p_value, 4),
        'hasil': kesimpulan,
        'sharpe_ratio': round(sharpe, 3) if sharpe is not None else None,
    })

hasil_df = pd.DataFrame(hasil)
print(hasil_df)

cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS uji_statistik")
cur.execute('''
CREATE TABLE uji_statistik (
    ticker TEXT PRIMARY KEY,
    p_value REAL,
    hasil TEXT,
    sharpe_ratio REAL,
    FOREIGN KEY (ticker) REFERENCES dim_saham(ticker)
)
''')
hasil_df.to_sql('uji_statistik', conn, if_exists='append', index=False)
conn.commit()
conn.close()
