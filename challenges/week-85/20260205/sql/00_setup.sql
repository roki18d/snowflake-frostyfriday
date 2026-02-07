
USE frostyfridaydb.week_085;

-- ============================================================
-- テーブル作成
-- ============================================================

CREATE OR REPLACE TABLE trade (
    type VARCHAR,
    id INT,
    ticker VARCHAR,
    datetime TIMESTAMP_TZ,
    price FLOAT,
    volume INT
);

CREATE OR REPLACE TABLE quotes(
    type VARCHAR,
    id INT,
    ticker VARCHAR,
    datetime TIMESTAMP_TZ,
    ask FLOAT,
    bid FLOAT
);


-- ============================================================
-- レコード挿入
-- ============================================================

-- TRUNCATE TABLE trade;
INSERT INTO trade VALUES
    ('trade', 2, 'AAPL', '2020-01-06 09:00:30.000+09:00', 305, 1),
    ('trade', 2, 'AAPL', '2020-01-06 09:01:00.000+09:00', 310, 2),
    ('trade', 2, 'AAPL', '2020-01-06 09:01:30.000+09:00', 308, 1),
    ('trade', 3, 'GOOGL', '2020-01-06 09:02:00.000+09:00', 1500, 2),
    ('trade', 3, 'GOOGL', '2020-01-06 09:03:00.000+09:00', 1520, 3),
    ('trade', 3, 'GOOGL', '2020-01-06 09:03:30.000+09:00', 1515, 1)
;
SELECT * FROM trade;

-- TRUNCATE TABLE quotes;
INSERT INTO quotes VALUES
    ('quote', 2, 'AAPL', '2020-01-06 08:59:59.999+09:00', 305, 304),
    ('quote', 2, 'AAPL', '2020-01-06 09:02:00.000+09:00', 311, 309),
    ('quote', 3, 'GOOGL', '2020-01-06 09:01:00.000+09:00', 1490, 1485),
    ('quote', 3, 'GOOGL', '2020-01-06 09:04:00.000+09:00', 1530, 1528)
;

INSERT INTO quotes VALUES
    ('quote', 2, 'AAPL', '2020-01-06 09:00:30.000+09:00', 307, 305),
    ('quote', 2, 'AAPL', '2020-01-06 09:01:30.000+09:00', 308, 306),
    ('quote', 3, 'GOOGL', '2020-01-06 09:02:00.000+09:00', 1502, 1498),
    ('quote', 3, 'GOOGL', '2020-01-06 09:03:30.000+09:00', 1518, 1513)
;
SELECT * FROM quotes;