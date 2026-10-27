CREATE OR REPLACE TABLE
  `yourprojectid.yourdataset.stg_movies_clean`
AS
WITH filtered AS (
  SELECT *
  FROM `yourprojectid.yourdataset.stg_movies_raw`
  WHERE
    status = 'Released'
    AND adult = FALSE
    AND release_date IS NOT NULL
    AND release_date >= DATE '1900-01-01'
    AND release_date <= CURRENT_DATE()
    AND runtime IS NOT NULL
    AND runtime > 0
    AND runtime >= 60
),
deduplicated AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY id
      ORDER BY
        vote_count DESC,
        revenue DESC
    ) AS rn
  FROM filtered
)
SELECT
  * EXCEPT (rn)
FROM deduplicated
WHERE rn = 1;