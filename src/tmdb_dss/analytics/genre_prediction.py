
import pandas as pd
import numpy as np

from .genre_trend import analyze_genre_trends


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

START_YEAR = 2020
END_YEAR = 2023

MARKET_SIZE_WEIGHT = 0.40
MARKET_GROWTH_WEIGHT = 0.35
RATING_WEIGHT = 0.25

# Confidence thresholds
HIGH_VOTE_COVERAGE = 60
MEDIUM_VOTE_COVERAGE = 40

HIGH_MIN_MOVIES = 300
MEDIUM_MIN_MOVIES = 100


# --------------------------------------------------
# 2. NORMALIZATION
# --------------------------------------------------

def minmax_score(series):
    """
    Normalize a metric to a 0-100 scale.

    Missing values receive a neutral score of 50.
    If all valid values are identical, assign 50
    because the metric cannot distinguish genres.
    """

    values = pd.to_numeric(series, errors="coerce")

    scores = pd.Series(
        50.0,
        index=series.index,
        dtype="float64"
    )

    valid = values.dropna()

    if valid.empty:
        return scores

    min_value = valid.min()
    max_value = valid.max()

    if max_value == min_value:
        return scores

    scores.loc[valid.index] = (
        (valid - min_value)
        / (max_value - min_value)
        * 100
    )

    return scores


# --------------------------------------------------
# 3. POTENTIAL CLASSIFICATION
# --------------------------------------------------

def classify_potential(score):
    """
    Classify genre potential based on its weighted score.
    """

    if pd.isna(score):
        return "Insufficient Data"

    if score < 25:
        return "Low"

    if score < 50:
        return "Moderate"

    if score < 75:
        return "High"

    return "Very High"


# --------------------------------------------------
# 4. CONFIDENCE CLASSIFICATION
# --------------------------------------------------

def classify_confidence(
    movie_count,
    vote_coverage_pct
):
    """
    Estimate confidence based on:
    - Number of movies in the genre
    - Percentage of movies with vote data

    This is a data-quality indicator,
    not a statistical confidence interval.
    """

    if pd.isna(movie_count) or pd.isna(vote_coverage_pct):
        return "Unavailable"

    if (
        movie_count >= HIGH_MIN_MOVIES
        and vote_coverage_pct >= HIGH_VOTE_COVERAGE
    ):
        return "High"

    if (
        movie_count >= MEDIUM_MIN_MOVIES
        and vote_coverage_pct >= MEDIUM_VOTE_COVERAGE
    ):
        return "Medium"

    return "Low"


# --------------------------------------------------
# 5. GENRE POTENTIAL PREDICTION
# --------------------------------------------------

def predict_genre_potential(
    start_year=START_YEAR,
    end_year=END_YEAR
):
    """
    Calculate a baseline genre potential score.

    Potential Score:
        40% Market Size
        35% Market Growth
        25% Rating

    The latest available year within the selected
    historical period is used for evaluation.

    Confidence Level is based on movie count
    and vote coverage, when available.
    """

    df = analyze_genre_trends(
        start_year=start_year,
        end_year=end_year,
        exclude_unknown=True
    )

    if df.empty:
        print("No genre trend data available.")
        return pd.DataFrame()

    # --------------------------------------------------
    # Select latest year
    # --------------------------------------------------

    latest_year = df["year"].max()

    latest_df = df[
        df["year"] == latest_year
    ].copy()

    if latest_df.empty:
        print("No genre data available for the latest year.")
        return pd.DataFrame()

    # --------------------------------------------------
    # Validate required columns
    # --------------------------------------------------

    required_columns = [
        "genre_name",
        "analysis_market_share",
        "genre_market_share_growth",
        "average_weighted_rating"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in latest_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns in genre trend data: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------
    # Calculate component scores
    # --------------------------------------------------

    # Market Size Score
    latest_df["market_score"] = minmax_score(
        latest_df["analysis_market_share"]
    )

    # Market Growth Score
    latest_df["market_growth_score"] = minmax_score(
        latest_df["genre_market_share_growth"]
    )

    # Rating Score
    latest_df["rating_score"] = minmax_score(
        latest_df["average_weighted_rating"]
    )

    # --------------------------------------------------
    # Calculate Potential Score
    # --------------------------------------------------

    latest_df["potential_score"] = (
        MARKET_SIZE_WEIGHT * latest_df["market_score"]
        + MARKET_GROWTH_WEIGHT * latest_df["market_growth_score"]
        + RATING_WEIGHT * latest_df["rating_score"]
    )

    # --------------------------------------------------
    # Classify Potential
    # --------------------------------------------------

    latest_df["potential_category"] = (
        latest_df["potential_score"]
        .apply(classify_potential)
    )

    # --------------------------------------------------
    # Calculate Confidence Level
    # --------------------------------------------------

    if (
        "movie_count" in latest_df.columns
        and "vote_coverage_pct" in latest_df.columns
    ):
        latest_df["confidence_level"] = latest_df.apply(
            lambda row: classify_confidence(
                row["movie_count"],
                row["vote_coverage_pct"]
            ),
            axis=1
        )
    else:
        latest_df["confidence_level"] = "Unavailable"

        print(
            "\nWARNING: movie_count or vote_coverage_pct "
            "is missing from genre trend data."
        )

        print(
            "Confidence Level cannot be calculated. "
            "Update the genre metrics view and loader."
        )

    # --------------------------------------------------
    # Build result
    # --------------------------------------------------

    output_columns = [
        "year",
        "genre_name",
        "potential_score",
        "potential_category",
        "confidence_level",
        "market_score",
        "market_growth_score",
        "rating_score",
        "analysis_market_share",
        "genre_market_share_growth",
        "average_weighted_rating"
    ]

    # Include data-quality fields when available
    optional_columns = [
        "movie_count",
        "vote_coverage_pct"
    ]

    for col in optional_columns:
        if col in latest_df.columns:
            output_columns.append(col)

    result = latest_df[output_columns].copy()

    result = result.sort_values(
        "potential_score",
        ascending=False
    ).reset_index(drop=True)

    return result


# --------------------------------------------------
# 6. MAIN
# --------------------------------------------------

if __name__ == "__main__":

    print("\n=== GENRE POTENTIAL PREDICTION ===")

    result = predict_genre_potential()

    if not result.empty:

        print(
            result.to_string(
                index=False,
                float_format=lambda x: f"{x:.2f}"
            )
        )

        print("\n=== POTENTIAL CATEGORY SUMMARY ===")

        print(
            result["potential_category"]
            .value_counts()
            .to_string()
        )

        print("\n=== CONFIDENCE LEVEL SUMMARY ===")

        print(
            result["confidence_level"]
            .value_counts()
            .to_string()
        )
