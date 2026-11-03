from pathlib import Path
from src.tmdb_dss.config import DSS_DATASET
from src.tmdb_dss.connection import (
    get_bigquery_client
)


SQL_DIR = Path("sql")


def run_all_sql():

    client = get_bigquery_client()

    files = sorted(
        SQL_DIR.glob("*.sql")
    )

    for file in files:

        print(f"Running {file.name}")

        sql = file.read_text(
            encoding="utf-8"
        )
        sql = sql.replace("dsstmdb.tmdbdw", DSS_DATASET)

        job = client.query(sql)

        job.result()

        print(
            f"Completed: {file.name}"
        )


if __name__ == "__main__":

    run_all_sql()