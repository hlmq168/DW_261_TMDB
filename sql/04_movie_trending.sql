CREATE OR REPLACE VIEW
  `dsstmdb.tmdbdw.vw_movie_trending`
AS

SELECT
    bm.movie_sk,
    bm.tmdb_id,
    bm.title,
    bm.release_year,

    bm.popularity,
    bm.vote_average,
    bm.vote_count,
    bm.weighted_rating,

    bm.budget,
    bm.revenue,
    bm.roi_percent,
    bm.profit,

    STRING_AGG(
        DISTINCT g.genre_name,
        ', '
    ) AS genres

FROM
    `dsstmdb.tmdbdw.vw_movie_business_metrics` bm

LEFT JOIN
    `dsstmdb.tmdbdw.bridge_movie_genre` bg
ON
    bm.movie_sk = bg.movie_sk

LEFT JOIN
    `dsstmdb.tmdbdw.dim_genre` g
ON
    bg.genre_sk = g.genre_sk

WHERE
    bm.popularity IS NOT NULL

GROUP BY
    bm.movie_sk,
    bm.tmdb_id,
    bm.title,
    bm.release_year,
    bm.popularity,
    bm.vote_average,
    bm.vote_count,
    bm.weighted_rating,
    bm.budget,
    bm.revenue,
    bm.roi_percent,
    bm.profit;