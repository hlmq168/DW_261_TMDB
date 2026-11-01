SELECT
    table_name
FROM
    `dsstmdb.tmdbdw.INFORMATION_SCHEMA.TABLES`
ORDER BY
    table_name;

SELECT 'fact_movie' AS table_name,
       COUNT(*) AS total_rows
FROM `dsstmdb.tmdbdw.fact_movie`

UNION ALL

SELECT 'dim_movie', COUNT(*)
FROM `dsstmdb.tmdbdw.dim_movie`

UNION ALL

SELECT 'bridge_movie_genre', COUNT(*)
FROM `dsstmdb.tmdbdw.bridge_movie_genre`;
