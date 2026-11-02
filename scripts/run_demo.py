from src.tmdb_dss.analytics.genre_trend import (
    analyze_genre_trends
)

from src.tmdb_dss.analytics.genre_prediction import (
    predict_genre_potential
)

from src.tmdb_dss.analytics.trending import (
    get_trending_movies
)

from src.tmdb_dss.service import (
    analyze_investment
)


print("\n1. GENRE TREND ANALYSIS")

trends = analyze_genre_trends()

print(trends.tail(10))


print("\n2. GENRE POTENTIAL")

potential = predict_genre_potential()

print(potential.head(10))


print("\n3. TRENDING MOVIES")

trending = get_trending_movies(
    min_votes=100,
    top_n=20
)

print(trending.head(20))


print("\n4. INVESTMENT ANALYSIS")

result = analyze_investment(
    budget=50_000_000,
    genres=["Action"],
    objective="HIGH_ROI",
    top_n=20
)

print(
    result["investment_candidates"].head(20)
)