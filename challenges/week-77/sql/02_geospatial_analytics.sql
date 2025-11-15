
-- ------------------------------------------------------------
-- 様々な Snowflake 地理空間関数
-- ------------------------------------------------------------

SELECT 
    name,
    geography,
    -- 2. Output
    ST_GEOHASH(geography) AS geohash,
    -- 3. Constructors
    ST_MAKEPOINT(12.482917, 41.893382) AS point_rome,
    -- 5. Relationships
    ST_DISTANCE(geography, point_rome) / 1000 AS distance_km_from_rome,
    -- 4. Accessors
    ST_DIMENSION(geography) AS dimension, -- 0: Point, 1: LineString, 2: Polygon
    ST_SRID(geography) AS srid,
    -- 8. H3
    H3_POINT_TO_CELL(geography, 5) AS h3_cell,
FROM italy_arcgis_points
LIMIT 100
;


-- ------------------------------------------------------------
-- 距離の計算 (ST_DISTANCE vs HAVERSINE）
-- ------------------------------------------------------------

SELECT 
  ST_DISTANCE(
    TO_GEOGRAPHY('POINT(-121.8212 36.8252)'),  -- San Francisco
    TO_GEOGRAPHY('POINT(13.4814 52.5015)')  -- Berlin
  ) / 1000 AS d_km_st_gg,
  HAVERSINE(
    36.8252, -121.8212,  -- San Francisco
    52.5015, 13.4814  -- Berlin
  ) AS d_km_haversine,
;

-- d_km_st_gg: 9182.410992278
-- d_km_haversine: 9182.396579476