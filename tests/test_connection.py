from src.tmdb_dss.connection import (
    get_bigquery_client
)

def test_connection():

    client = get_bigquery_client()

    result = client.query(
        "SELECT 1 AS test"
    ).to_dataframe()

    assert result.iloc[0]["test"] == 1

    print("BigQuery connection successful!")