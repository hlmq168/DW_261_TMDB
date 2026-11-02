from ..analytics.genre_prediction import (
    predict_genre_potential
)

from .investment_ranking import (
    rank_movies_by_objective
)


def get_genre_recommendations():
    return predict_genre_potential()


def recommend_movies(
    candidates,
    objective="BALANCED",
    genre_potential=None,
    movie_genres=None
):

    if genre_potential is None:
        genre_potential = get_genre_recommendations()

    return rank_movies_by_objective(
        df=candidates,
        objective=objective,
        genre_potential=genre_potential,
        movie_genres=movie_genres
    )