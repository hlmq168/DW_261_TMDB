
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics.pairwise import cosine_similarity

from ..data_loader import load_content_features


class ContentBasedRecommender:

    def __init__(self):

        self.data = load_content_features()

        self.movies = self.data["movies"]

        self.similarity = None

        self.movie_index = {}

    def fit(self):

        genres = self.data["genres"]
        companies = self.data["companies"]

        movie_ids = self.movies["movie_sk"].tolist()

        self.movie_index = {
            movie_id: i
            for i, movie_id in enumerate(movie_ids)
        }

        genre_matrix = genres.pivot_table(
            index="movie_sk",
            columns="genre_name",
            values="weight",
            aggfunc="sum",
            fill_value=0
        )

        company_matrix = companies.pivot_table(
            index="movie_sk",
            columns="company_name",
            values="weight",
            aggfunc="sum",
            fill_value=0
        )

        language_matrix = pd.get_dummies(
            self.movies.set_index("movie_sk")[
                "original_language_code"
            ],
            prefix="language",
            dtype=float
        )

        country_matrix = pd.get_dummies(
            self.movies.set_index("movie_sk")[
                "primary_country"
            ],
            prefix="country",
            dtype=float
        )

        genre_matrix = genre_matrix.reindex(
            movie_ids,
            fill_value=0
        )

        company_matrix = company_matrix.reindex(
            movie_ids,
            fill_value=0
        )

        language_matrix = language_matrix.reindex(
            movie_ids,
            fill_value=0
        )

        country_matrix = country_matrix.reindex(
            movie_ids,
            fill_value=0
        )

        # Feature weights
        genre_matrix *= 0.60
        company_matrix *= 0.20
        language_matrix *= 0.10
        country_matrix *= 0.10

        features = pd.concat(
            [
                genre_matrix,
                company_matrix,
                language_matrix,
                country_matrix
            ],
            axis=1
        )

        self.similarity = cosine_similarity(
            csr_matrix(features.values),
            dense_output=False
        )

        return self

    def recommend(
        self,
        movie_sk,
        top_n=10
    ):

        if self.similarity is None:
            raise RuntimeError(
                "Model has not been fitted."
            )

        if movie_sk not in self.movie_index:
            raise ValueError(
                "Movie not found."
            )

        index = self.movie_index[movie_sk]

        scores = self.similarity.getrow(
            index
        ).toarray().ravel()

        scores[index] = -1

        top_indices = scores.argsort()[
            ::-1
        ][:top_n]

        result = self.movies.iloc[
            top_indices
        ].copy()

        result["similarity_score"] = (
            scores[top_indices]
        )

        return result.reset_index(drop=True)
