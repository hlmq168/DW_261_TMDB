CREATE OR REPLACE VIEW
  `dsstmdb.tmdbdw.vw_movie_business_metrics`
AS

WITH rating_population AS (
    SELECT
        vote_average,
        vote_count
    FROM
        `dsstmdb.tmdbdw.fact_movie`
    WHERE
        vote_average IS NOT NULL
        AND vote_count > 0
),

rating_parameters AS (
    SELECT
        AVG(vote_average) AS global_mean,
        APPROX_QUANTILES(vote_count, 100)[OFFSET(80)]
            AS minimum_votes
    FROM
        rating_population
),

base AS (
    SELECT
        f.movie_sk,
        m.tmdb_id,
        m.title,
        m.original_title,

        d.full_date AS release_date,
        d.year AS release_year,

        m.runtime,
        m.original_language_code,
        m.primary_country,

        f.budget,
        f.revenue,

        f.popularity,
        f.vote_average,
        f.vote_count,

        f.has_financials,
        f.usable_for_roi,
        f.is_notable,

        CASE
            WHEN f.usable_for_roi
            THEN SAFE_DIVIDE(
                f.revenue - f.budget,
                f.budget
            ) * 100
        END AS roi_percent,

        CASE
            WHEN f.has_financials
            THEN f.revenue - f.budget
        END AS profit,

        rp.global_mean,
        rp.minimum_votes,

        SAFE_DIVIDE(
            f.vote_count,
            f.vote_count + rp.minimum_votes
        ) * f.vote_average
        +
        SAFE_DIVIDE(
            rp.minimum_votes,
            f.vote_count + rp.minimum_votes
        ) * rp.global_mean
        AS weighted_rating

    FROM
        `dsstmdb.tmdbdw.fact_movie` f

    JOIN
        `dsstmdb.tmdbdw.dim_movie` m
    ON
        f.movie_sk = m.movie_sk

    JOIN
        `dsstmdb.tmdbdw.dim_date` d
    ON
        f.release_date_sk = d.date_sk

    CROSS JOIN
        rating_parameters rp
)

SELECT
    *,
    CASE
        WHEN usable_for_roi AND roi_percent >= 100
            THEN 'Excellent'
        WHEN usable_for_roi AND roi_percent >= 20
            THEN 'Good'
        WHEN usable_for_roi AND roi_percent >= 0
            THEN 'Break-even'
        WHEN usable_for_roi
            THEN 'Loss'
        ELSE 'Not Eligible'
    END AS roi_tier

FROM base;