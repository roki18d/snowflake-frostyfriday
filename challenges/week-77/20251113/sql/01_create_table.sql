
USE DATABASE frostyfridaydb;
USE SCHEMA vol_038;

-- ------------------------------------------------------------
-- 外部ステージの確認
-- ------------------------------------------------------------

LIST @default/italy-arcgis-ndjson;

SELECT 
    SPLIT_PART(metadata$filename, '/', 7) AS data_label,
    $1 AS v,
FROM 
    @default/italy-arcgis-ndjson
    (FILE_FORMAT => MY_JSON, PATTERN => '.*[.]ndjson')
WHERE data_label = 'waterways'
LIMIT 1000
;

-- ------------------------------------------------------------
-- raw テーブルの作成
-- ------------------------------------------------------------

-- points
CREATE OR REPLACE TABLE italy_arcgis_points__raw AS 
    SELECT $1 AS v
    FROM @default/italy-arcgis-ndjson (FILE_FORMAT => MY_JSON, PATTERN => '.*[.]ndjson')
    WHERE SPLIT_PART(metadata$filename, '/', 7) = 'points'
;
-- places
CREATE OR REPLACE TABLE italy_arcgis_places__raw AS 
    SELECT $1 AS v
    FROM @default/italy-arcgis-ndjson (FILE_FORMAT => MY_JSON, PATTERN => '.*[.]ndjson')
    WHERE SPLIT_PART(metadata$filename, '/', 7) = 'places'
;
-- railways
CREATE OR REPLACE TABLE italy_arcgis_railways__raw AS 
    SELECT $1 AS v
    FROM @default/italy-arcgis-ndjson (FILE_FORMAT => MY_JSON, PATTERN => '.*[.]ndjson')
    WHERE SPLIT_PART(metadata$filename, '/', 7) = 'railways'
;
-- roads
CREATE OR REPLACE TABLE italy_arcgis_roads__raw AS 
    SELECT $1 AS v
    FROM @default/italy-arcgis-ndjson (FILE_FORMAT => MY_JSON, PATTERN => '.*[.]ndjson')
    WHERE SPLIT_PART(metadata$filename, '/', 7) = 'roads'
;
-- waterways
CREATE OR REPLACE TABLE italy_arcgis_waterways__raw AS 
    SELECT $1 AS v
    FROM @default/italy-arcgis-ndjson (FILE_FORMAT => MY_JSON, PATTERN => '.*[.]ndjson')
    WHERE SPLIT_PART(metadata$filename, '/', 7) = 'waterways'
;

-- 加工済みテーブルの確認
SELECT * FROM italy_arcgis_waterways__raw LIMIT 10 ;

-- ------------------------------------------------------------
-- 加工済みテーブルの作成
-- ------------------------------------------------------------

-- points
CREATE OR REPLACE TABLE italy_arcgis_points AS 
    SELECT 
        v:properties.osm_id AS osm_id,
        v:properties.name::string AS name,
        v:properties.type::string AS type,
        try_to_geography(v:geometry) AS geography,
    FROM italy_arcgis_points__raw
;
-- places
CREATE OR REPLACE TABLE italy_arcgis_places AS 
    SELECT 
        v:properties.osm_id AS osm_id,
        v:properties.name::string AS name,
        v:properties.type::string AS type,
        try_to_geography(v:geometry) AS geography,
        FROM italy_arcgis_places__raw
;
-- railways
CREATE OR REPLACE TABLE italy_arcgis_railways AS 
    SELECT 
        v:properties.osm_id AS osm_id,
        v:properties.name::string AS name,
        v:properties.type::string AS type,
        try_to_geography(v:geometry) AS geography,
    FROM italy_arcgis_railways__raw
;
-- roads
CREATE OR REPLACE TABLE italy_arcgis_roads AS 
    SELECT 
        v:properties.osm_id AS osm_id,
        v:properties.name::string AS name,
        v:properties.type::string AS type,
        try_to_geography(v:geometry) AS geography,
    FROM italy_arcgis_roads__raw
;
-- waterways
CREATE OR REPLACE TABLE italy_arcgis_waterways AS 
    SELECT 
        v:properties.osm_id AS osm_id,
        v:properties.name::string AS name,
        v:properties.type::string AS type,
        try_to_geography(v:geometry) AS geography,
    FROM italy_arcgis_waterways__raw
;

-- 加工済みテーブルの確認
SELECT * FROM italy_arcgis_waterways LIMIT 10 ;

