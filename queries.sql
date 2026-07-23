-- =====================================================================
-- Query analisis untuk project Dampak Kebijakan Swasembada Pangan
-- terhadap Kinerja Saham Rantai Pasok Pangan di IDX
--
-- Jalankan lewat: python buat_database.py
-- (atau buka pangan_idx.db pakai DB Browser for SQLite untuk coba manual)
-- =====================================================================


-- QUERY 1: Ranking Saham Berdasarkan Return Kumulatif per Periode
-- Teknik: Window function RANK() OVER (PARTITION BY ... ORDER BY ...)
-- Menjawab: saham mana yang paling unggul/tertinggal di tiap periode observasi?
SELECT
    periode,
    ticker,
    tahap_rantai_pasok,
    return_kumulatif,
    RANK() OVER (PARTITION BY periode ORDER BY return_kumulatif DESC) AS peringkat
FROM ringkasan_sektor
WHERE tahap_rantai_pasok != 'Benchmark (IHSG)'
ORDER BY periode, peringkat;


-- QUERY 2: Saham dengan Volatilitas di Atas Rata-Rata Tahapnya Sendiri
-- Teknik: CTE (WITH ...) + agregasi per grup, lalu di-JOIN balik ke data detail
-- Menjawab: saham mana yang lebih fluktuatif dibanding "teman satu tahap"-nya?
WITH rata_rata_volatilitas_tahap AS (
    SELECT
        tahap_rantai_pasok,
        periode,
        AVG(volatilitas) AS avg_volatilitas_tahap
    FROM ringkasan_sektor
    WHERE tahap_rantai_pasok != 'Benchmark (IHSG)'
    GROUP BY tahap_rantai_pasok, periode
)
SELECT
    r.ticker,
    r.tahap_rantai_pasok,
    r.periode,
    r.volatilitas,
    ROUND(a.avg_volatilitas_tahap, 2) AS avg_volatilitas_tahap
FROM ringkasan_sektor r
JOIN rata_rata_volatilitas_tahap a
    ON r.tahap_rantai_pasok = a.tahap_rantai_pasok AND r.periode = a.periode
WHERE r.volatilitas > a.avg_volatilitas_tahap
ORDER BY r.periode, r.tahap_rantai_pasok;


-- QUERY 3: Deteksi Golden Cross / Death Cross (Persilangan MA20 vs MA50)
-- Teknik: Window function LAG() untuk bandingkan nilai hari ini vs hari sebelumnya
-- Menjawab: kapan tepatnya sinyal perubahan tren muncul untuk tiap saham?
WITH ma_dengan_hari_sebelumnya AS (
    SELECT
        tanggal,
        ticker,
        ma20,
        ma50,
        LAG(ma20) OVER (PARTITION BY ticker ORDER BY tanggal) AS ma20_kemarin,
        LAG(ma50) OVER (PARTITION BY ticker ORDER BY tanggal) AS ma50_kemarin
    FROM indikator_teknikal
    WHERE ma20 IS NOT NULL AND ma50 IS NOT NULL
)
SELECT
    tanggal,
    ticker,
    CASE
        WHEN ma20_kemarin <= ma50_kemarin AND ma20 > ma50 THEN 'Golden Cross (bullish)'
        WHEN ma20_kemarin >= ma50_kemarin AND ma20 < ma50 THEN 'Death Cross (bearish)'
    END AS sinyal
FROM ma_dengan_hari_sebelumnya
WHERE (ma20_kemarin <= ma50_kemarin AND ma20 > ma50)
   OR (ma20_kemarin >= ma50_kemarin AND ma20 < ma50)
ORDER BY ticker, tanggal;


-- QUERY 4: Jumlah Hari Overbought vs Oversold per Saham
-- Teknik: Conditional aggregation dengan CASE WHEN di dalam COUNT()
-- Menjawab: saham mana yang paling sering di zona ekstrem (RSI>70 atau RSI<30)?
SELECT
    ticker,
    tahap_rantai_pasok,
    COUNT(CASE WHEN rsi14 > 70 THEN 1 END) AS hari_overbought,
    COUNT(CASE WHEN rsi14 < 30 THEN 1 END) AS hari_oversold,
    COUNT(rsi14) AS total_hari_dengan_rsi
FROM indikator_teknikal
GROUP BY ticker, tahap_rantai_pasok
ORDER BY hari_overbought DESC;


-- QUERY 5: Perbandingan Rata-Rata Return per Tahap Rantai Pasok (Periode 1 vs 2)
-- Teknik: Self-JOIN untuk menjejerkan 2 periode dalam 1 baris per tahap
-- Menjawab: tahap rantai pasok mana yang paling terdampak pergantian periode?
SELECT
    p1.tahap_rantai_pasok,
    ROUND(AVG(p1.return_kumulatif), 2) AS avg_return_periode1,
    ROUND(AVG(p2.return_kumulatif), 2) AS avg_return_periode2
FROM ringkasan_sektor p1
JOIN ringkasan_sektor p2
    ON p1.ticker = p2.ticker
    AND p1.tahap_rantai_pasok = p2.tahap_rantai_pasok
WHERE p1.periode = 'Periode 1 (sebelum Okt 2024)'
    AND p2.periode = 'Periode 2 (sesudah Okt 2024)'
GROUP BY p1.tahap_rantai_pasok;
