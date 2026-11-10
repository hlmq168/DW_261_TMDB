# TMDB Data Warehouse — One-command pipeline

This package adds `main.py` to orchestrate the existing steps:

1. Run the original `split.py` to split the source CSV into 9 parts.
2. Upload the parts in order into one BigQuery raw table.
3. Execute `clean.sql` to create `stg_movies_clean`.
4. Execute `table.sql` to build the 7 Data Warehouse tables.

The supplied `split.py`, `clean.sql`, and `table.sql` are copied unchanged into this package. `main.py` configures the generic identifiers when submitting SQL to BigQuery.

## Files

- `main.py` — one-command orchestrator.
- `split.py` — original CSV splitting script.
- `clean.sql` — original cleaning SQL.
- `table.sql` — original Data Warehouse SQL.
- `requirements.txt` — Python dependency.
- `README_DEPLOY.md` — this guide.

## 1. Put the CSV in the expected location

```text
Raw Data/TMDB_movie_dataset_v11.csv
```

Keep `main.py`, `split.py`, `clean.sql`, and `table.sql` in the package root.

## 2. Configure identifiers

Edit the top of `main.py`:

```python
PROJECT_ID = "YOUR_PROJECT_ID"
DATASET_ID = "YOUR_DATASET"
```

Use a Google Cloud project ID and an existing BigQuery dataset. The script creates/replaces these tables:
- `stg_movies_raw`
- `stg_movies_clean`
- `dim_date`
- `dim_movie`
- `dim_genre`
- `dim_company`
- `fact_movie`
- `bridge_movie_genre`
- `bridge_movie_company`

**Warning:** the supplied SQL uses `CREATE OR REPLACE TABLE`; running the pipeline replaces those tables. Back up any existing data you need to keep.

## 3. Install the dependency

```powershell
python -m pip install -r requirements.txt
```

## 4. Authenticate

One option is Google Cloud CLI:

```powershell
gcloud auth application-default login
```

This requires the Google Cloud CLI to be installed. Authenticate as an account with permission to create/load/query BigQuery tables in the selected project and dataset.

## 5. Run everything

From the package directory:

```powershell
python main.py
```

The script stops if a required file is missing or a BigQuery job fails. It prints progress for each stage.

## Important details

- The source CSV is not included in this ZIP.
- The first part uses schema autodetection; subsequent parts append to that schema. All parts must have the same columns in the same order and compatible data types.
- BigQuery load/query permissions and Sandbox limits still apply.
- The original SQL/Python files are not edited. `main.py` performs identifier substitution when submitting SQL.

## Interface Documentation

For instructions on setting up and running the project interface, including the frontend and backend, please refer to **[README_DEPLOY.md](README_DEPLOY.md)**.