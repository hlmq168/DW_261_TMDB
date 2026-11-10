import pandas as pd
from functools import lru_cache
from google.cloud import bigquery

from .config import DSS_DATASET
from .connection import get_bigquery_client
from .recommendation.content_based import load_or_build_recommender
from .recommendation.hybrid import calculate_hybrid_score
from .decision.decision_engine import run_investment_analysis


def analyze_investment(
    budget,
    genres=None,
    objective="BALANCED",
    min_votes=100,
    top_n=20
):
    """
    Public service interface for the investment DSS.

    Parameters
    ----------
    budget : float
        Maximum investment budget.
    genres : str or list, optional
        Target movie genres.
    objective : str
        Investment objective:
        BALANCED, HIGH_ROI, HIGH_PROFIT, POPULARITY, LOW_RISK.
    min_votes : int
        Minimum number of votes.
    top_n : int
        Number of top investment candidates to return.

    Returns
    -------
    dict
        Investment analysis results.
    """

    if budget is None or budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    return run_investment_analysis(
        budget=budget,
        genres=genres,
        objective=objective,
        min_votes=min_votes,
        top_n=top_n
    )

def to_df(rows):
    if rows is None:
        return pd.DataFrame()

    if isinstance(rows, pd.DataFrame):
        return rows.copy()

    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def get_content_recommender():
    return load_or_build_recommender()


def load_candidate_metrics(candidate_ids):
    client = get_bigquery_client()

    query = f"""
        SELECT
            dm.tmdb_id,
            bm.weighted_rating,
            bm.roi_tier
        FROM `{DSS_DATASET}.vw_movie_business_metrics` bm
        JOIN `{DSS_DATASET}.dim_movie` dm
            USING (movie_sk)
        WHERE dm.tmdb_id IN UNNEST(@movie_ids)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "movie_ids",
                "INT64",
                candidate_ids,
            )
        ]
    )

    return client.query(
        query,
        job_config=job_config,
    ).to_dataframe()


def get_movie_recommendations(
    movie_id,
    top_n=100,
    content_weight=0.50,
    rating_weight=0.30,
    business_weight=0.20,
):
    recommender = get_content_recommender()

    similar_movies = to_df(
        recommender.recommend(
            movie_id,
            top_n=top_n,
        )
    )

    if similar_movies.empty:
        return pd.DataFrame()

    similar_movies["id"] = (
        similar_movies["id"].astype("int64")
    )

    metrics = load_candidate_metrics(
        similar_movies["id"].tolist()
    )

    if metrics.empty:
        return pd.DataFrame()

    metrics["tmdb_id"] = (
        metrics["tmdb_id"].astype("int64")
    )

    recommendations = similar_movies.merge(
        metrics,
        left_on="id",
        right_on="tmdb_id",
        how="inner",
    )

    if recommendations.empty:
        return recommendations

    return calculate_hybrid_score(
        recommendations,
        content_weight=content_weight,
        rating_weight=rating_weight,
        business_weight=business_weight,
    )