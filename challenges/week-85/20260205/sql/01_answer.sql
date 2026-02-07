USE frostyfridaydb.week_085;

SELECT * FROM trade;
SELECT * FROM quotes;

-- ============================================================
-- 方法1: ASOF JOIN を使わない場合（ウィンドウ関数使用）
-- ============================================================
WITH matched_quotes AS (
    SELECT
        t.type,
        t.id,
        t.ticker,
        t.datetime AS trade_datetime,
        t.price AS trade_price,
        t.volume AS trade_volume,
        q.datetime AS quote_datetime,
        q.bid,
        q.ask,
        -- 取引時刻以前の気配値の中で、最も新しいものを特定するためのランク付け
        ROW_NUMBER() OVER (
            PARTITION BY t.id, t.datetime
            ORDER BY q.datetime DESC
        ) AS rn
    FROM
        trade t
    INNER JOIN
        quotes q
    ON
        t.ticker = q.ticker
        AND q.datetime <= t.datetime  -- 取引時刻以前の気配値のみ
)
SELECT
    type,
    id,
    ticker,
    trade_datetime,
    trade_price,
    trade_volume,
    quote_datetime,
    bid,
    ask
FROM
    matched_quotes
WHERE
    rn = 1  -- 最も新しい気配値のみを選択
ORDER BY
    ticker,
    trade_datetime
;


-- ============================================================
-- 方法2: ASOF JOIN を使用
-- ============================================================
-- 各取引に対して、取引時刻以前で最も新しい気配値を対応付ける
-- https://docs.snowflake.com/en/sql-reference/constructs/asof-join


SELECT
    t.type,
    t.id,
    t.ticker,
    t.datetime AS trade_datetime,
    t.price AS trade_price,
    t.volume AS trade_volume,
    q.datetime AS quote_datetime,
    q.bid,
    q.ask
FROM
    trade t
ASOF JOIN
    quotes q
MATCH_CONDITION(t.datetime >= q.datetime)
ON t.ticker = q.ticker
ORDER BY
    t.ticker,
    t.datetime
;