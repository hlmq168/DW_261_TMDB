import pandas as pd
import numpy as np

from ..data_loader import load_genre_trends


def calculate_growth(series):
    """
    Calculate year-over-year percentage growth.
    Returns NaN when the previous value is zero or missing.
    """
    previous = series.shift(1)

    result = (
        (series - previous)
        / previous.replace(0, np.nan)
    ) * 100

    return result.replace(
        [np.inf, -np.inf],
        np.nan
    )


def analyze_genre_trends(
    start_year=None,
    end_year=None,
    exclude_unknown=True
):
    """
    Analyze yearly genre trends.

    Uses known_genre_market_share for genre comparisons.
    Excludes Unknown from genre ranking by default.
    """

    df = load_genre_trends()

    if df.empty:
        return df

    # Normalize genre names
    df["genre_name"] = (
        df["genre_name"]
        .astype("string")
        .str.strip()
    )

    # Exclude Unknown from genre analysis
    if exclude_unknown:
        df = df[
            df["genre_name"].str.lower() != "unknown"
        ].copy()

    # Filter years
    if start_year is not None:
        df = df[df["year"] >= start_year]

    if end_year is not None:
        df = df[df["year"] <= end_year]

    if df.empty:
        return df

    df = df.sort_values(
        ["genre_name", "year"]
    ).copy()

    # Use known genre market share
    if "known_genre_market_share" in df.columns:
        df["analysis_market_share"] = (
            df["known_genre_market_share"]
        )
    else:
        df["analysis_market_share"] = (
            df["genre_market_share"]
        )

    # Metrics for growth analysis
    metrics = [
        "analysis_market_share",
        "weighted_movie_count",
        "total_revenue",
        "average_weighted_rating"
    ]

    for metric in metrics:
        df[f"{metric}_growth"] = (
            df.groupby("genre_name")[metric]
            .transform(calculate_growth)
        )

    # Rename growth column for readability
    df = df.rename(
        columns={
            "analysis_market_share_growth":
                "genre_market_share_growth"
        }
    )

    return df.reset_index(drop=True)


def get_latest_genre_trends():
    """
    Return latest available genre trends,
    excluding Unknown and ranking by known genre market share.
    """

    df = analyze_genre_trends()

    if df.empty:
        return df

    latest_year = df["year"].max()

    result = df[
        df["year"] == latest_year
    ].copy()

    return result.sort_values(
        "analysis_market_share",
        ascending=False
    ).reset_index(drop=True)


def classify_genre_growth(
    growth,
    threshold=5
):
    """
    Classify genre based on market share growth.
    """

    if pd.isna(growth):
        return "Insufficient data"

    if growth >= threshold:
        return "Growing"

    if growth <= -threshold:
        return "Declining"

    return "Stable"


def get_genre_opportunity():
    """
    Generate a basic genre opportunity overview.

    This is a descriptive screening result,
    not a guaranteed investment prediction.
    """

    df = get_latest_genre_trends()

    if df.empty:
        return df

    df["growth_status"] = (
        df["genre_market_share_growth"]
        .apply(classify_genre_growth)
    )

    df["opportunity_rank"] = (
        df["analysis_market_share"].rank(
            ascending=False,
            method="dense"
        )
    )

    return df.sort_values(
        ["opportunity_rank"]
    ).reset_index(drop=True)


if __name__ == "__main__":

    print("\n=== RAW GENRE TREND DATA ===")

    raw_df = load_genre_trends()

    print(raw_df.head(10).to_string(index=False))

    print("\n=== ANALYZED GENRE TRENDS ===")

    analyzed_df = analyze_genre_trends()

    print(analyzed_df.head(10).to_string(index=False))

    print("\n=== LATEST GENRE TRENDS ===")

    latest_df = get_latest_genre_trends()

    print(latest_df.to_string(index=False))

    print("\n=== GENRE OPPORTUNITY OVERVIEW ===")

    opportunity_df = get_genre_opportunity()

    print(
        opportunity_df[
            [
                "genre_name",
                "analysis_market_share",
                "genre_market_share_growth",
                "growth_status",
                "opportunity_rank"
            ]
        ].to_string(index=False)
    )