import ast
import json
import re
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize, MultiLabelBinarizer

from ..data_loader import (
    load_recommendation_movies,
    get_recommendation_source_metadata
)

def multilabel_tokenizer(text):
    """Extract complete category names without splitting multi-word labels."""
    return re.findall(r'"([^"]+)"', text)


class ContentBasedRecommender:

    FEATURE_WEIGHTS = {
        "overview": 0.50,
        "keywords": 0.40,
        "genre": 0.10
    }

    CACHE_DIR = Path("data/recommendation_cache")
    MODEL_PATH = CACHE_DIR / "content_based_model.joblib"
    METADATA_PATH = CACHE_DIR / "content_based_metadata.json"

    def __init__(self, data=None):

        self.movies = self._load_movies(data)

        self.features = {}
        self.movie_index = {}
        self.vectorizers = {}
        self.feature_slices = {}
        self.overview_word_matrix = None
        self.word_char_matrix = None
        self.word_index = {}
        self.word_vectorizer = None
        self.word_char_vectorizer = None

    def _load_movies(self, data):
        if data is not None:
            movies = data["movies"].copy()

        else:
            print("Loading cleaned movie data from BigQuery...")

            movies = load_recommendation_movies()

        movies["id"] = pd.to_numeric(
            movies["id"],
            errors="coerce"
        )

        movies = movies.dropna(
            subset=["id"]
        ).copy()

        movies["id"] = movies["id"].astype("int64")

        movies = movies.drop_duplicates(
            subset=["id"]
        ).reset_index(drop=True)

        movies["release_year"] = pd.to_datetime(
            movies["release_date"],
            errors="coerce"
        ).dt.year

        print(f"Movies loaded: {len(movies):,}")

        return movies

    @staticmethod
    def _prepare_text(value):

        if value is None or pd.isna(value):
            return ""

        return str(value).strip()

    @staticmethod
    def _parse_list(value):

        if value is None or pd.isna(value):
            return []

        if isinstance(value, (list, tuple, set)):
            items = list(value)

        else:
            text = str(value).strip()

            if not text or text.lower() in {
                "nan", "none", "null", "[]", "{}"
            }:
                return []

            items = None

            if text.startswith("[") and text.endswith("]"):

                try:
                    result = json.loads(text)

                    if isinstance(result, list):
                        items = result

                except (ValueError, TypeError):
                    pass

                if items is None:

                    with warnings.catch_warnings():
                        warnings.simplefilter(
                            "ignore", SyntaxWarning
                        )

                        try:
                            result = ast.literal_eval(text)

                            if isinstance(result, list):
                                items = result

                        except (
                            ValueError,
                            SyntaxError,
                            TypeError
                        ):
                            pass

            if items is None:
                items = text.split(",")

        result = []

        for item in items:

            if isinstance(item, dict):
                item = item.get("name", "")

            if item is None:
                continue

            item = str(item).strip()

            if item and item.lower() not in {
                "unknown", "none", "null", "nan"
            }:
                result.append(item)

        return result

    def _build_text_block(
        self,
        column,
        max_features=50000
    ):

        texts = self.movies[column].map(
            self._prepare_text
        )

        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            max_features=max_features,
            min_df=5,
            max_df=0.85,
            ngram_range=(4, 7),
            sublinear_tf=True,
            dtype=np.float32
        )

        try:
            matrix = vectorizer.fit_transform(texts)

        except ValueError:
            matrix = csr_matrix(
                (len(self.movies), 0),
                dtype=np.float32
            )

        self.vectorizers[column] = vectorizer

        return matrix.tocsr()

    def _build_multilabel_block(
        self,
        column,
        max_features=None
    ):

        parsed = self.movies[column].apply(
            self._parse_list
        )

        documents = parsed.apply(
            lambda values: " ".join(
                f'"{value}"'
                for value in values
            )
        )

        vectorizer = TfidfVectorizer(
            tokenizer=multilabel_tokenizer,
            token_pattern=None,
            lowercase=True,
            max_features=max_features,
            min_df=2,
            dtype=np.float32
        )

        try:
            matrix = vectorizer.fit_transform(documents)

        except ValueError:
            matrix = csr_matrix(
                (len(self.movies), 0),
                dtype=np.float32
            )

        self.vectorizers[column] = vectorizer

        return matrix.tocsr()

    def _build_categorical_block(self, column):

        values = (
            self.movies[column]
            .fillna("")
            .astype("string")
            .str.strip()
            .str.lower()
        )

        invalid = {
            "", "unknown", "none", "null", "nan", "und"
        }

        values = values.mask(
            values.isin(invalid)
        )

        codes, categories = pd.factorize(
            values,
            sort=False
        )

        valid = codes >= 0
        rows = np.flatnonzero(valid)

        matrix = csr_matrix(
            (
                np.ones(len(rows), dtype=np.float32),
                (rows, codes[valid])
            ),
            shape=(
                len(self.movies),
                len(categories)
            ),
            dtype=np.float32
        )

        return normalize(
            matrix,
            norm="l2",
            axis=1,
            copy=False
        )

    def _build_binary_genre_block(self, column):

        parsed = self.movies[column].apply(
            self._parse_list
        )

        parsed = parsed.apply(
            lambda labels: list(dict.fromkeys(
                label.strip().casefold()
                for label in labels
                if label.strip()
            ))
        )

        encoder = MultiLabelBinarizer(
            sparse_output=True
        )

        matrix = encoder.fit_transform(parsed)

        return matrix.astype(np.float32).tocsr()

    def _build_word_aggregation_features(self):

        texts = self.movies["overview"].map(
            self._prepare_text
        )

        # Word-level TF-IDF provides the importance of each word.
        self.word_vectorizer = TfidfVectorizer(
            token_pattern=r"(?u)\b[a-zA-Z]{3,}\b",
            stop_words="english",
            max_features=50000,
            sublinear_tf=True,
            dtype=np.float32
        )

        try:
            self.overview_word_matrix = (
                self.word_vectorizer.fit_transform(texts)
            )

        except ValueError:
            self.overview_word_matrix = csr_matrix(
                (len(self.movies), 0),
                dtype=np.float32
            )

            return

        # Build character representations for individual words.
        words = self.word_vectorizer.get_feature_names_out()

        self.word_char_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            dtype=np.float32
        )

        self.word_char_matrix = (
            self.word_char_vectorizer.fit_transform(words)
        ).tocsr()

        self.word_index = {
            word: index
            for index, word in enumerate(words)
        }

        print(
            f"Word aggregation vocabulary: {len(words):,} words"
        )

        print(
            "Word character features: "
            f"{self.word_char_matrix.shape[1]:,}"
        )

    def fit(self):

        required_columns = [
            "id",
            "overview",
            "keywords",
            "genres",
            "release_date"
        ]

        missing = [
            column
            for column in required_columns
            if column not in self.movies.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required columns: {missing}"
            )

        movie_ids = self.movies["id"].tolist()

        if len(set(movie_ids)) != len(movie_ids):
            raise ValueError("Movie IDs must be unique.")

        self.movie_index = {
            movie_id: index
            for index, movie_id in enumerate(movie_ids)
        }

        self.vectorizers = {}

        print("\nBuilding recommendation features...")

        self.features = {
            "overview": self._build_text_block("overview"),
            "keywords": self._build_multilabel_block("keywords"),
            "genre": self._build_binary_genre_block("genres")
        }

        print("\nBuilding word aggregation features...")

        self._build_word_aggregation_features()

        self.feature_slices = {}

        start = 0

        for name, matrix in self.features.items():

            end = start + matrix.shape[1]

            self.feature_slices[name] = slice(
                start,
                end
            )

            start = end

        print("\nFeature dimensions:")

        for name, matrix in self.features.items():

            print(
                f"{name:12s}: "
                f"{matrix.shape[1]:,} features, "
                f"{matrix.nnz:,} non-zero values"
            )

        print(f"\nTotal movies: {len(self.movies):,}")
        print("Feature construction completed.")

        return self

    def _genre_similarity(
        self,
        query_index,
        candidate_indices
    ):

        matrix = self.features["genre"]

        query = matrix[query_index]
        candidates = matrix[candidate_indices]

        query_count = query.nnz

        candidate_counts = np.asarray(
            candidates.getnnz(axis=1)
        ).ravel()

        intersections = (
            candidates @ query.T
        ).toarray().ravel()

        unions = (
            query_count
            + candidate_counts
            - intersections
        )

        similarities = np.divide(
            intersections,
            unions,
            out=np.zeros(
                len(candidate_indices),
                dtype=np.float32
            ),
            where=unions > 0
        )

        return similarities

    def _similarity_by_feature(
        self,
        query_index,
        candidate_indices,
        batch_size=20000
    ):

        contributions = {
            name: np.zeros(
                len(candidate_indices),
                dtype=np.float32
            )
            for name in self.features
        }

        for start in range(0, len(candidate_indices), batch_size):

            end = min(start + batch_size, len(candidate_indices))

            batch_indices = candidate_indices[start:end]

            for name, matrix in self.features.items():

                if name == "genre":

                    similarities = self._genre_similarity(
                        query_index,
                        batch_indices
                    )

                else:

                    query = matrix[query_index]
                    candidates = matrix[batch_indices]

                    similarities = (
                        candidates @ query.T
                    ).toarray().ravel()

                contributions[name][start:end] = (
                    similarities * self.FEATURE_WEIGHTS[name]
                )

        return contributions

    def recommend(
        self,
        movie_id,
        top_n=10
    ):

        if not self.features:
            raise RuntimeError(
                "Model has not been fitted."
            )

        if movie_id not in self.movie_index:
            raise ValueError("Movie not found.")

        if top_n <= 0:
            raise ValueError(
                "top_n must be greater than zero."
            )

        query_index = self.movie_index[movie_id]

        candidate_indices = np.arange(
            len(self.movies)
        )

        candidate_indices = candidate_indices[
            candidate_indices != query_index
        ]

        contributions = self._similarity_by_feature(
            query_index,
            candidate_indices
        )

        scores = np.zeros(
            len(candidate_indices),
            dtype=np.float32
        )

        for values in contributions.values():
            scores += values

        evidence = np.zeros(
            len(candidate_indices),
            dtype=np.float32
        )

        for name, matrix in self.features.items():

            query_available = (
                matrix[query_index].nnz > 0
            )

            candidate_available = np.asarray(
                matrix[candidate_indices].getnnz(axis=1)
            ).ravel() > 0

            if query_available:

                evidence += (
                    candidate_available
                    * self.FEATURE_WEIGHTS[name]
                )

        order = np.argsort(scores)[::-1][:top_n]

        selected_indices = candidate_indices[order]

        result = self.movies.iloc[
            selected_indices
        ].copy()

        result["similarity_score"] = scores[order]
        result["evidence_coverage"] = evidence[order]

        return result.reset_index(drop=True)

def load_or_build_recommender():
    ContentBasedRecommender.CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    current_metadata = get_recommendation_source_metadata()

    if (
        ContentBasedRecommender.MODEL_PATH.exists()
        and ContentBasedRecommender.METADATA_PATH.exists()
    ):

        try:

            with open(
                ContentBasedRecommender.METADATA_PATH,
                "r",
                encoding="utf-8"
            ) as file:

                saved_metadata = json.load(file)

            if saved_metadata == current_metadata:

                print("\nLoading cached recommendation model...")

                recommender = joblib.load(
                    ContentBasedRecommender.MODEL_PATH
                )

                if recommender.movies["id"].nunique() != recommender.movies.shape[0]:
                    raise ValueError("Cached model contains duplicate movie IDs.")

                print("Cached model loaded successfully.")

                return recommender

        except Exception as error:

            print(f"Cache could not be loaded: {error}")

    print("\nNo valid cache found.")
    print("Building recommendation model from BigQuery...")

    movies = load_recommendation_movies()

    recommender = ContentBasedRecommender(
        data={"movies": movies}
    )

    recommender.fit()

    temp_model_path = (
        ContentBasedRecommender.CACHE_DIR
        / "content_based_model.tmp"
    )

    joblib.dump(
        recommender,
        temp_model_path
    )

    temp_model_path.replace(
        ContentBasedRecommender.MODEL_PATH
    )

    temp_metadata_path = (
        ContentBasedRecommender.CACHE_DIR
        / "content_based_metadata.tmp"
    )

    with open(
        temp_metadata_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            current_metadata,
            file,
            indent=4
        )

    temp_metadata_path.replace(
        ContentBasedRecommender.METADATA_PATH
    )

    print("Recommendation model saved successfully.")

    return recommender