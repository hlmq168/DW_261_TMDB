CREATE OR REPLACE VIEW
  `dsstmdb.tmdbdw.vw_genre_current_performance`
AS

SELECT
    g.genre_name,

    COUNT(DISTINCT f.movie_sk) AS movie_count,

    AVG(f.popularity) AS average_popularity,

    AVG(bm.weighted_rating) AS average_weighted_rating,

    AVG(
        CASE
            WHEN f.usable_for_roi
            THEN bm.roi_percent
        END
    ) AS average_roi,

    AVG(
        CASE
            WHEN f.has_financials
            THEN bm.profit
        END
    ) AS average_profit

FROM
    `dsstmdb.tmdbdw.fact_movie` f

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

WHERE
    g.genre_name != 'Unknown'

GROUP BY
    g.genre_name;