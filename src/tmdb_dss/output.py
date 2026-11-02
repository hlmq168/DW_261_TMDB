
import math
import numpy as np
import pandas as pd


def normalize_value(value):
    """Convert values into JSON-compatible Python types."""

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(k): normalize_value(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [normalize_value(v) for v in value]

    if isinstance(value, pd.DataFrame):
        return normalize_dataframe(value)

    if isinstance(value, pd.Series):
        return normalize_value(value.to_dict())

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if pd.isna(value):
        return None

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    return value


def normalize_dataframe(df):
    """Convert DataFrame into JSON-compatible records."""

    clean_df = df.copy()

    clean_df = clean_df.astype(object)
    clean_df = clean_df.where(pd.notna(clean_df), None)

    records = clean_df.to_dict(orient="records")

    return normalize_value(records)


def normalize_output(result):
    """Normalize complete DSS output."""

    return normalize_value(result)
