-- ============================================================
-- TMDB DATA WAREHOUSE
-- Source: stg_movies_clean
-- Target: 7 existing DW tables
-- ============================================================


-- 1. DIM_DATE
-- One row per unique release date.

CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.dim_date` AS

SELECT DISTINCT
  CAST(FORMAT_DATE('%Y%m%d', release_date) AS INT64) AS date_sk,
  release_date AS full_date,
  EXTRACT(YEAR FROM release_date) AS year,
  EXTRACT(MONTH FROM release_date) AS month,
  EXTRACT(QUARTER FROM release_date) AS quarter,
  FORMAT_DATE('%B', release_date) AS month_name
FROM
  `yourprojectid.yourdataset.stg_movies_clean`
WHERE
  release_date IS NOT NULL;


-- 2. DIM_MOVIE
-- One row per movie.
-- movie_sk is a deterministic surrogate key for this load.

CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.dim_movie` AS

WITH movie_source AS (
  SELECT DISTINCT
    SAFE_CAST(id AS INT64) AS tmdb_id,
    imdb_id,
    title,
    original_title,
    runtime,
    original_language,
    production_countries
  FROM
    `yourprojectid.yourdataset.stg_movies_clean`
  WHERE
    SAFE_CAST(id AS INT64) IS NOT NULL
)

SELECT
  ROW_NUMBER() OVER (ORDER BY tmdb_id) AS movie_sk,
  tmdb_id,
  imdb_id,
  title,
  original_title,
  runtime,
  original_language AS original_language_code,

  CASE LOWER(TRIM(original_language))
    WHEN 'en' THEN 'English'
    WHEN 'vi' THEN 'Vietnamese'
    WHEN 'fr' THEN 'French'
    WHEN 'ja' THEN 'Japanese'
    WHEN 'ko' THEN 'Korean'
    WHEN 'zh' THEN 'Chinese'
    WHEN 'es' THEN 'Spanish'
    WHEN 'de' THEN 'German'
    WHEN 'it' THEN 'Italian'
    WHEN 'hi' THEN 'Hindi'
    WHEN 'pt' THEN 'Portuguese'
    WHEN 'ru' THEN 'Russian'
    WHEN 'th' THEN 'Thai'
    WHEN 'ar' THEN 'Arabic'
    WHEN 'id' THEN 'Indonesian'
    WHEN 'tr' THEN 'Turkish'
    WHEN 'unknown' THEN 'Unknown'
    ELSE
      CASE
        WHEN original_language IS NULL
          OR TRIM(original_language) = ''
          THEN 'Unknown'
        ELSE 'Unknown'
      END
  END AS original_language_name,

  COALESCE(
    NULLIF(TRIM(SPLIT(production_countries, ',')[SAFE_OFFSET(0)]), ''),
    'Unknown'
  ) AS primary_country

FROM movie_source;


-- 3. DIM_GENRE
-- Reserve genre_sk = -1 for Unknown.

CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.dim_genre` AS

WITH genre_names AS (
  SELECT DISTINCT
    TRIM(genre_name) AS genre_name
  FROM
    `yourprojectid.yourdataset.stg_movies_clean`,
    UNNEST(SPLIT(COALESCE(genres, ''), ',')) AS genre_name
  WHERE
    TRIM(genre_name) != ''
    AND LOWER(TRIM(genre_name)) != 'unknown'
)

SELECT
  -1 AS genre_sk,
  'Unknown' AS genre_name

UNION ALL

SELECT
  ROW_NUMBER() OVER (ORDER BY genre_name) AS genre_sk,
  genre_name
FROM genre_names;


-- 4. DIM_COMPANY
-- Reserve company_sk = -1 for Unknown.

CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.dim_company` AS

WITH company_names AS (
  SELECT DISTINCT
    TRIM(company_name) AS company_name
  FROM
    `yourprojectid.yourdataset.stg_movies_clean`,
    UNNEST(SPLIT(COALESCE(production_companies, ''), ',')) AS company_name
  WHERE
    TRIM(company_name) != ''
    AND LOWER(TRIM(company_name)) != 'unknown'
)

SELECT
  -1 AS company_sk,
  'Unknown' AS company_name

UNION ALL

SELECT
  ROW_NUMBER() OVER (ORDER BY company_name) AS company_sk,
  company_name
FROM company_names;


-- 5. FACT_MOVIE
-- One row per movie.
-- Convert zero budget/revenue to NULL.

CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.fact_movie` AS

SELECT
  m.movie_sk,
  CAST(FORMAT_DATE('%Y%m%d', s.release_date) AS INT64)
    AS release_date_sk,

  NULLIF(SAFE_CAST(s.budget AS INT64), 0) AS budget,
  NULLIF(SAFE_CAST(s.revenue AS INT64), 0) AS revenue,
  SAFE_CAST(s.popularity AS FLOAT64) AS popularity,
  SAFE_CAST(s.vote_average AS FLOAT64) AS vote_average,
  SAFE_CAST(s.vote_count AS INT64) AS vote_count,

  (
    NULLIF(SAFE_CAST(s.budget AS INT64), 0) IS NOT NULL
    AND NULLIF(SAFE_CAST(s.revenue AS INT64), 0) IS NOT NULL
  ) AS has_financials,

  (
    NULLIF(SAFE_CAST(s.budget AS INT64), 0) >= 100000
    AND NULLIF(SAFE_CAST(s.revenue AS INT64), 0) >= 100000
  ) AS usable_for_roi,

  SAFE_CAST(s.vote_count AS INT64) >= 10 AS is_notable,

  CURRENT_DATE() AS load_date

FROM
  `yourprojectid.yourdataset.stg_movies_clean` AS s
JOIN
  `yourprojectid.yourdataset.dim_movie` AS m
ON
  SAFE_CAST(s.id AS INT64) = m.tmdb_id
WHERE
  s.release_date IS NOT NULL;


-- 6. BRIDGE_MOVIE_GENRE
-- Split genres, remove duplicate pairs, use Unknown when absent.
-- Weight per movie sums to 1.

CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.bridge_movie_genre` AS

WITH genre_pairs AS (
  SELECT DISTINCT
    m.movie_sk,
    TRIM(g) AS genre_name
  FROM
    `yourprojectid.yourdataset.stg_movies_clean` AS s
  JOIN
    `yourprojectid.yourdataset.dim_movie` AS m
  ON
    SAFE_CAST(s.id AS INT64) = m.tmdb_id
  CROSS JOIN
    UNNEST(SPLIT(COALESCE(s.genres, ''), ',')) AS g
  WHERE
    TRIM(g) != ''
),

complete_pairs AS (
  SELECT
    movie_sk,
    genre_name
  FROM genre_pairs

  UNION DISTINCT

  SELECT
    m.movie_sk,
    'Unknown' AS genre_name
  FROM
    `yourprojectid.yourdataset.dim_movie` AS m
  WHERE NOT EXISTS (
    SELECT 1
    FROM genre_pairs AS p
    WHERE p.movie_sk = m.movie_sk
  )
),

weighted_pairs AS (
  SELECT
    movie_sk,
    genre_name,
    1.0 / COUNT(*) OVER (PARTITION BY movie_sk) AS weight
  FROM complete_pairs
)

SELECT
  p.movie_sk,
  g.genre_sk,
  p.weight
FROM weighted_pairs AS p
JOIN
  `yourprojectid.yourdataset.dim_genre` AS g
ON
  p.genre_name = g.genre_name;


-- 7. BRIDGE_MOVIE_COMPANY
-- Split production companies, remove duplicate pairs,
-- use Unknown when absent. Weight per movie sums to 1.

CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.bridge_movie_company` AS

WITH company_pairs AS (
  SELECT DISTINCT
    m.movie_sk,
    TRIM(c) AS company_name
  FROM
    `yourprojectid.yourdataset.stg_movies_clean` AS s
  JOIN
    `yourprojectid.yourdataset.dim_movie` AS m
  ON
    SAFE_CAST(s.id AS INT64) = m.tmdb_id
  CROSS JOIN
    UNNEST(SPLIT(COALESCE(s.production_companies, ''), ',')) AS c
  WHERE
    TRIM(c) != ''
),

complete_pairs AS (
  SELECT
    movie_sk,
    company_name
  FROM company_pairs

  UNION DISTINCT

  SELECT
    m.movie_sk,
    'Unknown' AS company_name
  FROM
    `yourprojectid.yourdataset.dim_movie` AS m
  WHERE NOT EXISTS (
    SELECT 1
    FROM company_pairs AS p
    WHERE p.movie_sk = m.movie_sk
  )
),

weighted_pairs AS (
  SELECT
    movie_sk,
    company_name,
    1.0 / COUNT(*) OVER (PARTITION BY movie_sk) AS weight
  FROM complete_pairs
)

SELECT
  p.movie_sk,
  c.company_sk,
  p.weight
FROM weighted_pairs AS p
JOIN
  `yourprojectid.yourdataset.dim_company` AS c
ON
  p.company_name = c.company_name;