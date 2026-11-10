import logging
import threading
import time

import pandas as pd
from fastapi import APIRouter, HTTPException

from tmdb_dss.connection import get_bigquery_client
from tmdb_dss.config import DSS_DATASET
from tmdb_dss.analytics.genre_trend import (
    get_latest_genre_trends,
    analyze_genre_trends,
)
from tmdb_dss.analytics.genre_prediction import (
    predict_genre_potential,
)
from tmdb_dss.analytics.trending import (
    get_trending_movies,
)
from tmdb_dss.output import normalize_output


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)

CACHE_TTL_SECONDS = 300
TRENDING_MIN_VOTES = 100
TRENDING_TOP_N = 10

_cache = {"payload": None, "expires_at": 0.0}
_cache_lock = threading.Lock()


def select_columns(df, columns):
    """Select only columns available in a DataFrame."""
    if not isinstance(df, pd.DataFrame):
        return df

    return df[
        [column for column in columns if column in df.columns]
    ].copy()


def get_total_movies():
    client = get_bigquery_client()

    query = f"""
        SELECT COUNT(DISTINCT tmdb_id) AS total_movies
        FROM `{DSS_DATASET}.dim_movie`
        WHERE tmdb_id IS NOT NULL
    """

    result = client.query(query).result()
    return next(iter(result)).total_movies


def build_overview(total_movies, latest_genres):
    if latest_genres.empty:
        return {
            "total_movies": total_movies,
            "latest_year": None,
            "genre_count": 0,
            "leading_genre": None,
            "leading_genre_market_share": None,
        }

    # Don't rely on row order: pick the genre with the highest share.
    ranked = latest_genres.dropna(subset=["analysis_market_share"])
    leading = (
        ranked.loc[ranked["analysis_market_share"].idxmax()]
        if not ranked.empty
        else None
    )

    return {
        "total_movies": total_movies,
        "latest_year": int(latest_genres["year"].max()),
        "genre_count": len(latest_genres),
        "leading_genre": (
            leading["genre_name"] if leading is not None else None
        ),
        "leading_genre_market_share": (
            float(leading["analysis_market_share"])
            if leading is not None
            else None
        ),
    }


def build_dashboard():
    total_movies = get_total_movies()

    trends = analyze_genre_trends()
    latest_genres = get_latest_genre_trends()
    potential = predict_genre_potential()
    trending = get_trending_movies(
        min_votes=TRENDING_MIN_VOTES,
        top_n=TRENDING_TOP_N,
    )

    result = {
        "overview": build_overview(total_movies, latest_genres),

        "meta": {
            "trending_min_votes": TRENDING_MIN_VOTES,
            "trending_top_n": TRENDING_TOP_N,
        },

        "genre_distribution": select_columns(
            latest_genres,
            [
                "genre_name",
                "analysis_market_share",
                "movie_count",
                "average_weighted_rating",
            ],
        ),

        "genre_trends": select_columns(
            trends,
            [
                "year",
                "genre_name",
                "analysis_market_share",
                "genre_market_share_growth",
                "average_weighted_rating",
            ],
        ),

        "genre_potential": potential,

        "trending_movies": select_columns(
            trending,
            [
                "trending_rank",
                "title",
                "release_year",
                "genres",
                "popularity",
                "vote_count",
                "weighted_rating",
                "popularity_percentile",
                "popularity_category",
            ],
        ),
    }

    return normalize_output(result)


@router.get("/")
def get_dashboard(refresh: bool = False):
    """Return dashboard data, cached for CACHE_TTL_SECONDS.

    Pass ?refresh=true to force a rebuild.
    """
    with _cache_lock:
        if (
            not refresh
            and _cache["payload"] is not None
            and time.monotonic() < _cache["expires_at"]
        ):
            return _cache["payload"]

    try:
        payload = build_dashboard()
    except Exception:
        # Full details go to the server log, not to the browser.
        logger.exception("Dashboard data retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Dashboard data retrieval failed. Please try again later.",
        )

    with _cache_lock:
        _cache["payload"] = payload
        _cache["expires_at"] = time.monotonic() + CACHE_TTL_SECONDS

    return payload