from google.cloud import bigquery
from .config import PROJECT_ID

def get_bigquery_client():

    client = bigquery.Client(
        project=PROJECT_ID
    )

    return client