
import pandas as pd
import numpy as np

def minmax(series):

    series = series.astype(float)

    minimum = series.min()
    maximum = series.max()

    if pd.isna(minimum) or maximum == minimum:
        return pd.Series(
            50.0,
            index=series.index
        )

    return (
        (series - minimum)
        / (maximum - minimum)
    ) * 100


def calculate_hybrid_score(
    df,
    content_weight=0.50,
    rating_weight=0.30,
    business_weight=0.20
):

    df = df.copy()

    weights = [
        content_weight,
        rating_weight,
        business_weight
    ]

    if any(w < 0 for w in weights):
        raise ValueError("Weights cannot be negative.")

    if not np.isclose(sum(weights), 1.0):
        raise ValueError("Weights must sum to 1.")

    df["content_score"] = (
        df["similarity_score"].clip(0, 0.30) / 0.30
    ) * 100

    df["rating_score"] = minmax(
        df["weighted_rating"]
    )

    df["business_score"] = np.select(
        [
            df["roi_tier"] == "Excellent",
            df["roi_tier"] == "Good",
            df["roi_tier"] == "Break-even",
            df["roi_tier"] == "Loss"
        ],
        [100, 80, 60, 20],
        default=50
    )

    df["final_score"] = (
        df["content_score"] * content_weight
        +
        df["rating_score"] * rating_weight
        +
        df["business_score"] * business_weight
    )

    return df.sort_values(
        "final_score",
        ascending=False
    ).reset_index(drop=True)
