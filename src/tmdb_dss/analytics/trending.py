
import pandas as pd


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

DEFAULT_MIN_VOTES = 100
DEFAULT_TOP_N = 50

# Popularity percentile thresholds
HOT_THRESHOLD = 0.90
TRENDING_THRESHOLD = 0.70


# --------------------------------------------------
# 2. DATA PREPARATION
# --------------------------------------------------

def prepare_trending_data(df):
    """
    Clean and prepare movie trending data.
    """

    if df.empty:
        return df

    df = df.copy()

    required_columns = [
        "movie_sk",
        "title",
        "popularity",
        "vote_count",
        "weighted_rating",
        "genres"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # Convert numeric fields
    numeric_columns = [
        "popularity",
        "vote_count",
        "weighted_rating"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # Normalize genre text
    df["genres"] = (
        df["genres"]
        .fillna("")
        .astype(str)
    )

    return df


# --------------------------------------------------
# 3. GENRE FILTERING
# --------------------------------------------------

def filter_by_genres(df, genres=None):
    """
    Filter movies by exact genre names.

    SQL genres format:
        Action, Adventure, Science Fiction
    """

    if not genres:
        return df

    if isinstance(genres, str):
        genres = [genres]

    selected_genres = {
        str(g).strip().casefold()
        for g in genres
        if str(g).strip()
    }

    if not selected_genres:
        return df

    def contains_selected_genre(value):
        movie_genres = {
            genre.strip().casefold()
            for genre in str(value).split(",")
            if genre.strip()
        }

        return bool(
            movie_genres.intersection(selected_genres)
        )

    mask = df["genres"].apply(
        contains_selected_genre
    )

    return df[mask].copy()


# --------------------------------------------------
# 4. POPULARITY CLASSIFICATION
# --------------------------------------------------

def classify_popularity(percentile):
    """
    Classify movies based on relative popularity.

    This is a cross-sectional popularity classification,
    not a time-series trend prediction.
    """

    if pd.isna(percentile):
        return "Insufficient Data"

    if percentile >= HOT_THRESHOLD:
        return "Hot"

    if percentile >= TRENDING_THRESHOLD:
        return "Trending"

    return "Regular"


# --------------------------------------------------
# 5. TRENDING MOVIE ANALYSIS
# --------------------------------------------------

def get_trending_movies(
    genres=None,
    min_votes=DEFAULT_MIN_VOTES,
    top_n=DEFAULT_TOP_N
):
    """
    Retrieve and rank trending movies.

    Parameters
    ----------
    genres : str or list, optional
        Exact genre names used to filter movies.

    min_votes : int, default=100
        Minimum vote count.

    top_n : int, default=50
        Maximum number of movies returned.

    Returns
    -------
    pandas.DataFrame
        Ranked trending movies with popularity classification.
    """

    if top_n is not None and top_n < 1:
        raise ValueError("top_n must be greater than 0.")

    if min_votes is not None and min_votes < 0:
        raise ValueError("min_votes cannot be negative.")

    # Load data
    from ..data_loader import load_trending_movies

    df = load_trending_movies()

    if df.empty:
        print("No trending movie data available.")
        return df

    # Prepare data
    df = prepare_trending_data(df)

    # Filter valid popularity
    df = df[
        df["popularity"].notna()
        & (df["popularity"] >= 0)
    ].copy()

    # Filter minimum votes
    if min_votes is not None:
        df = df[
            df["vote_count"].notna()
            & (df["vote_count"] >= min_votes)
        ].copy()

    # Filter genres
    df = filter_by_genres(
        df,
        genres=genres
    )

    if df.empty:
        print("No movies match the selected filters.")
        return df

    # Rank by popularity and weighted rating
    df = df.sort_values(
        ["popularity", "weighted_rating"],
        ascending=[False, False],
        na_position="last"
    ).copy()

    # Assign ranking
    df["trending_rank"] = range(
        1,
        len(df) + 1
    )

    # Calculate relative popularity percentile
    df["popularity_percentile"] = (
        df["popularity"].rank(
            method="average",
            pct=True
        ) * 100
    )

    # Classify popularity
    df["popularity_category"] = (
        df["popularity_percentile"]
        .div(100)
        .apply(classify_popularity)
    )

    # Return top N
    if top_n is not None:
        df = df.head(top_n)

    return df.reset_index(drop=True)


# --------------------------------------------------
# 6. MAIN
# --------------------------------------------------

if __name__ == "__main__":

    print("\n=== TOP TRENDING MOVIES ===")

    result = get_trending_movies(
        min_votes=100,
        top_n=50
    )

    if not result.empty:

        display_columns = [
            "trending_rank",
            "title",
            "release_year",
            "genres",
            "popularity",
            "vote_count",
            "weighted_rating",
            "popularity_percentile",
            "popularity_category"
        ]

        display_columns = [
            col for col in display_columns
            if col in result.columns
        ]

        print(
            result[display_columns].to_string(
                index=False,
                float_format=lambda x: f"{x:.2f}"
            )
        )

        print("\n=== POPULARITY CATEGORY SUMMARY ===")

        print(
            result["popularity_category"]
            .value_counts()
            .to_string()
        )

        print("\n=== TOP ACTION MOVIES ===")

        action_movies = get_trending_movies(
            genres=["Action"],
            min_votes=100,
            top_n=10
        )

        if not action_movies.empty:
            print(
                action_movies[
                    [
                        "trending_rank",
                        "title",
                        "genres",
                        "popularity",
                        "weighted_rating"
                    ]
                ].to_string(index=False)
            )
