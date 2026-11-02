import pandas as pd

from ..analytics.genre_prediction import (
    predict_genre_potential
)

from ..data_loader import load_content_features

VALID_OBJECTIVES = {
    "BALANCED",
    "HIGH_ROI",
    "HIGH_PROFIT",
    "POPULARITY",
    "LOW_RISK"
}


def calculate_genre_potential_scores(
    movie_genres,
    genre_potential
):
    """
    Calculate weighted genre potential score for each movie.
    """

    required_genre_columns = {
        "movie_sk",
        "genre_name",
        "weight"
    }

    required_potential_columns = {
        "genre_name",
        "potential_score"
    }

    if not required_genre_columns.issubset(
        movie_genres.columns
    ):
        raise ValueError(
            "movie_genres is missing required columns."
        )

    if not required_potential_columns.issubset(
        genre_potential.columns
    ):
        raise ValueError(
            "genre_potential is missing required columns."
        )

    genres = movie_genres.copy()
    potentials = genre_potential.copy()

    genres["weight"] = pd.to_numeric(
        genres["weight"],
        errors="coerce"
    )

    potentials["potential_score"] = pd.to_numeric(
        potentials["potential_score"],
        errors="coerce"
    )

    # Keep the latest prediction for each genre
    if "year" in potentials.columns:

        potentials["year"] = pd.to_numeric(
            potentials["year"],
            errors="coerce"
        )

        potentials = potentials.sort_values(
            "year",
            ascending=False
        )

    potentials = potentials.drop_duplicates(
        subset=["genre_name"],
        keep="first"
    )

    merged = genres.merge(
        potentials[
            ["genre_name", "potential_score"]
        ],
        on="genre_name",
        how="inner"
    )

    merged = merged.dropna(
        subset=["potential_score"]
    )

    merged = merged[
        merged["weight"].notna()
        & (merged["weight"] > 0)
    ]

    merged["weighted_potential"] = (
        merged["potential_score"]
        * merged["weight"]
    )

    result = (
        merged.groupby("movie_sk")
        .agg(
            weighted_potential=(
                "weighted_potential",
                "sum"
            ),
            total_weight=(
                "weight",
                "sum"
            )
        )
        .reset_index()
    )

    result["genre_potential_score"] = (
        result["weighted_potential"]
        / result["total_weight"]
    )

    return result[
        ["movie_sk", "genre_potential_score"]
    ]


def rank_movies_by_objective(
    df,
    objective="BALANCED",
    genre_potential=None,
    movie_genres=None
):
    """
    Rank movies according to an investment objective.
    """

    objective = objective.upper()

    if objective not in VALID_OBJECTIVES:
        raise ValueError(
            f"Unsupported objective: {objective}. "
            f"Choose from {sorted(VALID_OBJECTIVES)}."
        )

    df = df.copy()

    required_columns = {
        "movie_sk",
        "popularity",
        "weighted_rating",
        "vote_count"
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    # Convert numeric fields
    numeric_columns = [
        "popularity",
        "weighted_rating",
        "vote_count",
        "roi_percent",
        "profit"
    ]

    for column in numeric_columns:

        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # Rating score: fixed scale 0-100
    df["rating_score"] = (
        df["weighted_rating"]
        .clip(0, 10)
        * 10
    )

    # Popularity score: relative to candidate population
    maximum = df["popularity"].max()

    if pd.notna(maximum) and maximum > 0:

        df["popularity_score"] = (
            df["popularity"].clip(lower=0)
            / maximum
            * 100
        )

    else:
        df["popularity_score"] = 0

    # Genre potential score
    if genre_potential is None:
        genre_potential = predict_genre_potential()

    if movie_genres is None:

        content_features = load_content_features()
        movie_genres = content_features["genres"]

    genre_scores = calculate_genre_potential_scores(
        movie_genres,
        genre_potential
    )

    df = df.merge(
        genre_scores,
        on="movie_sk",
        how="left"
    )

    # Neutral score for movies without matched genre potential.
    # Keep a flag so missing information remains visible.
    df["has_genre_potential"] = (
        df["genre_potential_score"].notna()
    )

    df["genre_potential_score"] = (
        df["genre_potential_score"].fillna(50)
    )

    # Financial scores
    if "roi_percent" in df.columns:

        # df["roi_score"] = (
        #     df["roi_percent"]
        #     .clip(-100, 300)
        #     .add(100)
        #     .div(400)
        #     .mul(100)
        # )
        df["roi_score"] = (
        df["roi_percent"].rank(pct=True) * 100
        )


    else:
        df["roi_score"] = float("nan")

    if "profit" in df.columns:

        df["profit_score"] = (
            df["profit"].rank(pct=True) * 100
        )

    else:
        df["profit_score"] = float("nan")

    # Vote count proxy
    df["risk_proxy_score"] = (
        df["vote_count"].rank(pct=True) * 100
    )

    # Objective-specific ranking
    if objective == "HIGH_ROI":

        eligible = (
            df["usable_for_roi"]
            .fillna(False)
            .astype(bool)
            & df["roi_percent"].notna()
        )

        df = df[eligible].copy()

        if df.empty:
            raise ValueError(
                "No ROI-eligible movies available."
            )

        df["decision_score"] = (
            df["roi_score"] * 0.60
            + df["rating_score"] * 0.20
            + df["popularity_score"] * 0.20
        )

    elif objective == "HIGH_PROFIT":

        df = df[
            df["profit"].notna()
        ].copy()

        if df.empty:
            raise ValueError(
                "No movies with valid profit data."
            )

        df["decision_score"] = (
            df["profit_score"] * 0.60
            + df["rating_score"] * 0.20
            + df["popularity_score"] * 0.20
        )

    elif objective == "POPULARITY":

        df["decision_score"] = (
            df["popularity_score"] * 0.50
            + df["rating_score"] * 0.30
            + df["genre_potential_score"] * 0.20
        )

    elif objective == "LOW_RISK":

        df["decision_score"] = (
            df["risk_proxy_score"] * 0.40
            + df["rating_score"] * 0.40
            + df["popularity_score"] * 0.20
        )

    else:

        df["decision_score"] = (
            df["popularity_score"] * 0.35
            + df["rating_score"] * 0.35
            + df["genre_potential_score"] * 0.30
        )

    df = df.sort_values(
        "decision_score",
        ascending=False
    ).reset_index(drop=True)

    df["investment_rank"] = (
        df.index + 1
    )

    return df