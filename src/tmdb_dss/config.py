import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "dsstmdb")
DATASET = os.getenv("BQ_DATASET", "tmdbdw")

if not PROJECT_ID or not DATASET:
    raise ValueError("Missing BigQuery configuration")

# Nếu bạn gom chung vào dataset tmdbdw:
DSS_DATASET = f"{PROJECT_ID}.{DATASET}"