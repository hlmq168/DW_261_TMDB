import json
from pathlib import Path

import joblib

from ..data_loader import load_genre_trends


CACHE_DIR = Path("data/recommendation_cache")

CACHE_FILE = CACHE_DIR / "genre_trends.joblib"
METADATA_FILE = CACHE_DIR / "genre_trends_metadata.json"


def get_cached_genre_trends(refresh=False):

    if CACHE_FILE.exists() and not refresh:
        print("Loading cached genre trends...")
        return joblib.load(CACHE_FILE)

    print("Loading genre trends from BigQuery...")

    df = load_genre_trends()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    temp_cache = CACHE_DIR / "genre_trends.tmp"

    joblib.dump(df, temp_cache)
    temp_cache.replace(CACHE_FILE)

    metadata = {
        "row_count": len(df),
        "columns": list(df.columns),
    }

    temp_metadata = CACHE_DIR / "genre_trends_metadata.tmp"

    with open(temp_metadata, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)

    temp_metadata.replace(METADATA_FILE)

    print("Genre trends cached successfully.")

    return df


def refresh_genre_trends():
    return get_cached_genre_trends(refresh=True)