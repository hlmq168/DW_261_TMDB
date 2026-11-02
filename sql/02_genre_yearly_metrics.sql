
CREATE OR REPLACE VIEW
  `dsstmdb.tmdbdw.vw_genre_yearly_metrics`
AS

WITH genre_data AS (
    SELECT
        d.year,
        g.genre_name,
        f.movie_sk,
        bg.weight,

        f.revenue,
        f.popularity,
        f.vote_count,

        bm.weighted_rating

    FROM
        `dsstmdb.tmdbdw.fact_movie` AS f

    INNER JOIN
        `dsstmdb.tmdbdw.dim_date` AS d
        ON f.release_date_sk = d.date_sk

    INNER JOIN
        `dsstmdb.tmdbdw.bridge_movie_genre` AS bg
        ON f.movie_sk = bg.movie_sk

    INNER JOIN
        `dsstmdb.tmdbdw.dim_genre` AS g
        ON bg.genre_sk = g.genre_sk

    INNER JOIN
        `dsstmdb.tmdbdw.vw_movie_business_metrics` AS bm
        ON f.movie_sk = bm.movie_sk
),

genre_aggregated AS (
    SELECT
        year,
        genre_name,

        -- 1. Total number of distinct movies
        COUNT(DISTINCT movie_sk) AS movie_count,

        -- 2. Weighted movie count
        SUM(
            COALESCE(weight, 0)
        ) AS weighted_movie_count,

        -- 3. Total weighted revenue
        SUM(
            COALESCE(revenue, 0) * COALESCE(weight, 0)
        ) AS total_revenue,

        -- 4. Average revenue weighted by genre weight
        SAFE_DIVIDE(
            SUM(
                CASE
                    WHEN revenue IS NOT NULL
                         AND weight > 0
                    THEN revenue * weight
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN revenue IS NOT NULL
                         AND weight > 0
                    THEN weight
                    ELSE 0
                END
            )
        ) AS average_revenue,

        -- 5. Average popularity weighted by genre weight
        SAFE_DIVIDE(
            SUM(
                CASE
                    WHEN popularity IS NOT NULL
                         AND weight > 0
                    THEN popularity * weight
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN popularity IS NOT NULL
                         AND weight > 0
                    THEN weight
                    ELSE 0
                END
            )
        ) AS average_popularity,

        -- 6. Average weighted rating
        -- Numerator and denominator use exactly the same conditions
        SAFE_DIVIDE(
            SUM(
                CASE
                    WHEN vote_count > 0
                         AND weighted_rating IS NOT NULL
                         AND weight > 0
                    THEN weighted_rating * weight
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN vote_count > 0
                         AND weighted_rating IS NOT NULL
                         AND weight > 0
                    THEN weight
                    ELSE 0
                END
            )
        ) AS average_weighted_rating

    FROM
        genre_data

    GROUP BY
        year,
        genre_name
)

SELECT
    *,

    -- 7. Genre market share (%)
    SAFE_DIVIDE(
        weighted_movie_count,
        SUM(weighted_movie_count)
            OVER (PARTITION BY year)
    ) * 100 AS genre_market_share

FROM
    genre_aggregated;
