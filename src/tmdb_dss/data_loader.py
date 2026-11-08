from .connection import get_bigquery_client
from .config import DSS_DATASET

def load_view(view_name):

    client = get_bigquery_client()

    query = f"""
        SELECT *
        FROM `{DSS_DATASET}.{view_name}`
    """

    df = client.query(query).to_dataframe()

    return df


def load_movie_metrics():

    return load_view(
        "vw_movie_business_metrics"
    )


def load_genre_trends():

    return load_view(
        "vw_genre_yearly_metrics"
    )


def load_genre_performance():

    return load_view(
        "vw_genre_current_performance"
    )


def load_trending_movies():

    return load_view(
        "vw_movie_trending"
    )

def load_content_features():

    client = get_bigquery_client()

    genre_query = f"""
        SELECT
            bg.movie_sk,
            g.genre_name,
            bg.weight
        FROM `{DSS_DATASET}.bridge_movie_genre` bg
        JOIN `{DSS_DATASET}.dim_genre` g
        USING (genre_sk)
        WHERE g.genre_name != 'Unknown'
    """

    company_query = f"""
        SELECT
            bc.movie_sk,
            c.company_name,
            bc.weight
        FROM `{DSS_DATASET}.bridge_movie_company` bc
        JOIN `{DSS_DATASET}.dim_company` c
        USING (company_sk)
        WHERE c.company_name != 'Unknown'
    """

    movie_query = f"""
        SELECT
            movie_sk,
            tmdb_id,
            title,
            original_language_code,
            primary_country
        FROM `{DSS_DATASET}.dim_movie`
    """

    return {
        "movies": client.query(movie_query).to_dataframe(),
        "genres": client.query(genre_query).to_dataframe(),
        "companies": client.query(company_query).to_dataframe()
    }

def load_recommendation_movies():

    client = get_bigquery_client()

    query = f"""
        SELECT
            id,
            title,
            overview,
            keywords,
            genres,
            release_date,
            popularity
        FROM `{DSS_DATASET}.stg_movies_clean`
        WHERE id IS NOT NULL
    """

    return client.query(query).to_dataframe()

def get_recommendation_source_metadata():

    client = get_bigquery_client()

    table = client.get_table(
        f"{DSS_DATASET}.stg_movies_clean"
    )

    return {
        "table_id": table.full_table_id,
        "etag": table.etag,
        "modified": (
            table.modified.isoformat()
            if table.modified else None
        ),
        "num_rows": table.num_rows
    }