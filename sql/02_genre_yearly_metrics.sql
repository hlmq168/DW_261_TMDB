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
        `dsstmdb.tmdbdw.fact_movie` f

    JOIN
        `dsstmdb.tmdbdw.dim_date` d
    ON
        f.release_date_sk = d.date_sk

    JOIN
        `dsstmdb.tmdbdw.bridge_movie_genre` bg
    ON
        f.movie_sk = bg.movie_sk

    JOIN
        `dsstmdb.tmdbdw.dim_genre` g
    ON
        bg.genre_sk = g.genre_sk

    JOIN
        `dsstmdb.tmdbdw.vw_movie_business_metrics` bm
    ON
        f.movie_sk = bm.movie_sk
),

genre_aggregated AS (
    SELECT
        year,
        genre_name,

        COUNT(DISTINCT movie_sk) AS movie_count,

        SUM(weight) AS weighted_movie_count,

        SUM(
            COALESCE(revenue, 0) * weight
        ) AS total_revenue,

        SUM(
            CASE
                WHEN revenue IS NOT NULL
                THEN revenue * weight
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN revenue IS NOT NULL
                    THEN weight
                    ELSE 0
                END
            ),
            0
        ) AS average_revenue,

        SUM(
            popularity * weight
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN popularity IS NOT NULL
                    THEN weight
                    ELSE 0
                END
            ),
            0
        ) AS average_popularity,

        SUM(
            weighted_rating * weight
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN vote_count > 0
                    THEN weight
                    ELSE 0
                END
            ),
            0
        ) AS average_weighted_rating

    FROM genre_data

    GROUP BY
        year,
        genre_name
)

SELECT
    *,

    SAFE_DIVIDE(
        weighted_movie_count,
        SUM(weighted_movie_count)
            OVER (PARTITION BY year)
    ) * 100 AS genre_market_share

FROM genre_aggregated;