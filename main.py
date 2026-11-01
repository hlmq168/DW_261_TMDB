from pathlib import Path
import subprocess
import sys

from google.cloud import bigquery

# ============================================================
# CONFIGURATION: edit these values for your Google Cloud setup
# ============================================================
PROJECT_ID = "dsstmdb"
DATASET_ID = "tmdbdw"

RAW_TABLE = "stg_movies_raw"
CLEAN_TABLE = "stg_movies_clean"

SOURCE_CSV = Path("Raw Data/TMDB_movie_dataset_v11.csv")
SPLIT_SCRIPT = Path("split.py")
PARTS_DIR = Path("tmdb_parts")

CLEAN_SQL = Path("clean.sql")
DW_SQL = Path("table.sql")


def fq_table(table_name: str) -> str:
    return f"`{PROJECT_ID}.{DATASET_ID}.{table_name}`"


def configure_sql(sql: str) -> str:
    return sql.replace(
        "yourprojectid.yourdataset.",
        f"{PROJECT_ID}.{DATASET_ID}.",
    )


def run_bigquery_sql(client: bigquery.Client, sql_path: Path, label: str):
    if not sql_path.is_file():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    sql = sql_path.read_text(encoding="utf-8")
    sql = configure_sql(sql)

    print(f"\nRunning {label}: {sql_path} ...")
    job = client.query(sql)
    job.result()
    print(f"{label} completed.")


def main():
    if PROJECT_ID == "YOUR_PROJECT_ID" or DATASET_ID == "YOUR_DATASET":
        raise SystemExit(
            "Edit PROJECT_ID and DATASET_ID at the top of main.py before running."
        )

    if not SOURCE_CSV.is_file():
        raise SystemExit(
            f"Source CSV not found: {SOURCE_CSV}\n"
            "Place TMDB_movie_dataset_v11.csv inside the 'Raw Data' folder."
        )

    for path in (SPLIT_SCRIPT, CLEAN_SQL, DW_SQL):
        if not path.is_file():
            raise SystemExit(f"Required file not found: {path}")

    print("[1/4] Splitting CSV into 9 parts...")
    subprocess.run([sys.executable, str(SPLIT_SCRIPT)], check=True)

    part_files = sorted(
        PARTS_DIR.glob("tmdb_part_*.csv"),
        key=lambda p: int(p.stem.rsplit("_", 1)[1]),
    )
    if not part_files:
        raise SystemExit(f"No split CSV files found in {PARTS_DIR.resolve()}")

    client = bigquery.Client(project=PROJECT_ID)
    raw_table_id = f"{PROJECT_ID}.{DATASET_ID}.{RAW_TABLE}"

    print(f"\n[2/4] Uploading {len(part_files)} CSV parts to {raw_table_id}...")
    for index, part_file in enumerate(part_files):
        print(f"  [{index + 1}/{len(part_files)}] {part_file.name}")

        config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=(index == 0),
            write_disposition=(
                bigquery.WriteDisposition.WRITE_TRUNCATE
                if index == 0
                else bigquery.WriteDisposition.WRITE_APPEND
            ),
        )
        with part_file.open("rb") as f:
            job = client.load_table_from_file(f, raw_table_id, job_config=config)
        job.result()
        print(f"      Loaded {job.output_rows:,} rows.")

    raw_table = client.get_table(raw_table_id)
    print(f"Upload complete: {raw_table.num_rows:,} rows in {raw_table.full_table_id}")

    print("\n[3/4] Cleaning data...")
    run_bigquery_sql(client, CLEAN_SQL, "Cleaning SQL")

    print("\n[4/4] Building the 7 Data Warehouse tables...")
    run_bigquery_sql(client, DW_SQL, "Data Warehouse SQL")

    print("\nPIPELINE COMPLETED")
    print(f"Raw table:   {PROJECT_ID}.{DATASET_ID}.{RAW_TABLE}")
    print(f"Clean table: {PROJECT_ID}.{DATASET_ID}.{CLEAN_TABLE}")
    print("DW tables: dim_date, dim_movie, dim_genre, dim_company, fact_movie,")
    print("           bridge_movie_genre, bridge_movie_company")


if __name__ == "__main__":
    main()
