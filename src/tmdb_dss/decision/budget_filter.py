import pandas as pd

from ..data_loader import (
    load_movie_metrics,
    load_content_features
)


def filter_movies_by_budget(
    budget=None,
    genres=None,
    min_votes=100,
    require_positive_roi=False,
    min_budget=None,
    max_budget=None,
    start_year=None,
    end_year=None,
    min_rating=None,
    known_budget_only=True
):

    df = load_movie_metrics().copy()

    # Normalize numeric columns
    numeric_columns = [
        "budget",
        "vote_count",
        "vote_average",
        "weighted_rating",
        "release_year",
        "roi_percent"
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # Backward compatibility:
    # budget is interpreted as maximum budget.
    if budget is not None:

        if max_budget is not None:
            raise ValueError(
                "Use either budget or max_budget, not both."
            )

        max_budget = budget

    if min_budget is not None and min_budget < 0:
        raise ValueError(
            "min_budget cannot be negative."
        )

    if max_budget is not None and max_budget <= 0:
        raise ValueError(
            "max_budget must be greater than zero."
        )

    if (
        min_budget is not None
        and max_budget is not None
        and min_budget > max_budget
    ):
        raise ValueError(
            "min_budget cannot exceed max_budget."
        )

    # Budget filtering
    # budget_known = (
    # df["budget"].notna()
    # & (df["budget"] > 0)
    # )
    if known_budget_only:

        df = df[
            df["budget"].notna()
            & (df["budget"] > 0)
        ].copy()

    if min_budget is not None:

        df = df[
            (
                df["budget"].isna()
                | (df["budget"] <= 0)
                | (df["budget"] >= min_budget)
            )
        ].copy()

    if max_budget is not None:

        df = df[
            (
                df["budget"].isna()
                | (df["budget"] <= 0)
                | (df["budget"] <= max_budget)
            )
        ].copy()

    # Vote count filtering
    if min_votes is not None:

        df = df[
            df["vote_count"].notna()
            & (df["vote_count"] >= min_votes)
        ].copy()

    # Rating filtering
    if min_rating is not None:

        df = df[
            df["weighted_rating"].notna()
            & (df["weighted_rating"] >= min_rating)
        ].copy()

    # Release year filtering
    if start_year is not None:

        df = df[
            df["release_year"].notna()
            & (df["release_year"] >= start_year)
        ].copy()

    if end_year is not None:

        df = df[
            df["release_year"].notna()
            & (df["release_year"] <= end_year)
        ].copy()

    # Positive ROI filtering
    if require_positive_roi:

        roi_eligible = (
            df["usable_for_roi"]
            .fillna(False)
            .astype(bool)
        )

        df = df[
            roi_eligible
            & df["roi_percent"].notna()
            & (df["roi_percent"] > 0)
        ].copy()

    # Exact genre filtering
    if genres:

        if isinstance(genres, str):
            genres = [genres]

        selected_genres = {
            genre.strip().casefold()
            for genre in genres
            if isinstance(genre, str) and genre.strip()
        }

        if selected_genres:

            content_features = load_content_features()
            genre_data = content_features["genres"]

            matched_movies = genre_data[
                genre_data["genre_name"]
                .astype(str)
                .str.strip()
                .str.casefold()
                .isin(selected_genres)
            ]["movie_sk"].drop_duplicates()

            df = df[
                df["movie_sk"].isin(matched_movies)
            ].copy()

    return df.reset_index(drop=True)