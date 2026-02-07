USE frostyfridaydb.week_085;

-- 1. 大規模な売上テーブル（100万件）の生成
SET NUMBER_OF_ROWS = 1000000;

CREATE OR REPLACE TABLE sales_large AS
SELECT
    UUID_STRING() AS transaction_id,
    -- 2024年の1年間の中でランダムな秒数足した日時を生成
    DATEADD(second, UNIFORM(1, 31536000, RANDOM()), '2024-01-01'::TIMESTAMP_NTZ) AS transaction_time,
    -- 100円〜10,000円のランダムな売上
    UNIFORM(100, 10000, RANDOM()) AS amount_jpy
FROM TABLE(GENERATOR(ROWCOUNT => $NUMBER_OF_ROWS))
; -- 100万行

SELECT count(*) FROM sales_large;
SELECT * FROM sales_large LIMIT 10;

-- 2. 大規模な為替レートテーブル（1分刻みで1年分 = 約52万件）の生成
CREATE OR REPLACE TABLE fx_rates_large AS
SELECT
    DATEADD(minute, SEQ4(), '2024-01-01'::TIMESTAMP_NTZ) AS rate_time,
    'USD' AS currency,
    -- 130円〜150円の間で変動するレートを擬似生成
    (UNIFORM(130, 150, RANDOM()) + UNIFORM(0, 99, RANDOM()) / 100)::NUMBER(10, 2) AS rate_usd
FROM TABLE(GENERATOR(ROWCOUNT => 525600)); -- 60分 * 24時間 * 365日

-- レコードの中身を確認
SELECT * FROM fx_rates_large LIMIT 10;
SELECT count(*) FROM fx_rates_large;
SELECT * FROM sales_large LIMIT 10;
SELECT count(*) FROM sales_large;

-- Result Cache を無効化
ALTER SESSION SET USE_CACHED_RESULT = FALSE;

-- 比較用：従来の重たいクエリ
-- （注意: XSウェアハウスだと数分かかるか、タイムアウトする可能性があります）
SELECT
    s.transaction_id,
    s.transaction_time,
    r.rate_usd
FROM sales_large s
LEFT JOIN fx_rates_large r
    ON r.rate_time <= s.transaction_time -- 決済日時より前のレートを全て結合候補にする（これが重い！）
QUALIFY ROW_NUMBER() OVER (PARTITION BY s.transaction_id ORDER BY r.rate_time DESC) = 1 -- その中で最新を取る
ORDER BY s.transaction_id
LIMIT 100; -- 結果確認用

-- 本命：AS OF JOIN クエリ
SELECT
    s.transaction_id,
    s.transaction_time,
    r.rate_time AS rate_timestamp,
    r.rate_usd,
    s.amount_jpy,
    ROUND(s.amount_jpy / r.rate_usd, 2) AS amount_usd
FROM sales_large s
ASOF JOIN fx_rates_large r
    MATCH_CONDITION(s.transaction_time >= r.rate_time) -- 結合条件
ORDER BY s.transaction_id
LIMIT 100;