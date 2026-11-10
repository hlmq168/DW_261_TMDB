from ..analytics.genre_trend import analyze_genre_trends
from ..analytics.genre_prediction import predict_genre_potential
from ..analytics.trending import get_trending_movies

from .budget_filter import filter_movies_by_budget
from .investment_strategy import recommend_movies

from ..output import normalize_output


def run_investment_analysis(
    budget,
    genres=None,
    objective="BALANCED",
    min_votes=100,
    top_n=20
):
    """
    Run the end-to-end movie investment analysis.

    Returns a standardized JSON-compatible dictionary.
    """

    # Validate inputs
    if budget is None or budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    if top_n <= 0:
        raise ValueError("top_n must be greater than zero.")

    if min_votes < 0:
        raise ValueError("min_votes cannot be negative.")

    # 1. Historical genre trends
    genre_trends = analyze_genre_trends()

    # 2. Genre potential
    potential = predict_genre_potential()

    # 3. Determine target genres
    if genres is None:
        target_genres = (
            potential
            .head(5)["genre_name"]
            .dropna()
            .tolist()
        )

    elif isinstance(genres, str):
        target_genres = [genres]

    else:
        target_genres = list(genres)

    # 4. Trending movies
    trending = get_trending_movies(
        genres=target_genres,
        min_votes=min_votes,
        top_n=100
    )

    # 5. Budget filtering
    candidates = filter_movies_by_budget(
        budget=budget,
        genres=target_genres,
        min_votes=min_votes
    )

    # 6. Investment ranking
    ranked = recommend_movies(
        candidates=candidates,
        objective=objective,
        genre_potential=potential
    )

    top_candidates = ranked.head(top_n)
    top_recommendations = ranked.head(5)

    # 7. Build standardized output
    result = {
        "metadata": {
            "status": "success",
            "engine": "TMDB Investment DSS",
            "version": "1.0"
        },

        "input": {
            "budget": budget,
            "genres": target_genres,
            "objective": objective,
            "min_votes": min_votes,
            "top_n": top_n
        },

        "market_analysis": {
            "genre_trends": genre_trends,
            "genre_potential": potential,
            "trending_movies": trending
        },

        "investment_analysis": {
            "candidate_count": len(candidates),
            "ranking_method": objective,
            "ranking": top_candidates
        },

        "summary": {
            "recommended_movie_count": len(top_candidates),
            "top_recommendations": top_recommendations,
            "warnings": [
                "ROI is based on available TMDB financial data.",
                "ROI does not represent actual investor return."
            ]
        }
    }

    return normalize_output(result)
