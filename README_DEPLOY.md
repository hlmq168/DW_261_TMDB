# TMDB Decision Support System

A movie analytics and decision-support application built using the TMDB dataset, Google BigQuery, FastAPI, and React.

The system provides three main features:

- **Dashboard:** Explore movie trends, genre performance, and predicted genre potential.
- **Movie Recommendations:** Find similar movies using content similarity and hybrid ranking.
- **Investment Analysis:** Filter and rank movie candidates based on budget, genre, and investment objectives.

## Tech Stack

- **Data Warehouse:** Google BigQuery
- **Backend:** Python, FastAPI, Pandas
- **Frontend:** React.js, JavaScript, CSS
- **Data Processing:** Python, SQL

## Project Structure

```text
TMDB_Dataloader/
├── backend/          # FastAPI application and API routes
├── frontend/         # React application
├── src/tmdb_dss/     # Analytics and decision-support modules
├── main.py           # BigQuery data loading pipeline
├── split.py          # Source CSV splitting
├── clean.sql         # Data cleaning
├── table.sql         # Data Warehouse table creation
├── requirements.txt
├── README_DEPLOY.md
├── README_DSS.md
└── README.md
```

## Getting Started

### 1. Configure BigQuery

Configure your Google Cloud project and BigQuery dataset, then authenticate:

```powershell
gcloud auth application-default login
```

For initial data loading and Data Warehouse setup, see [README_DEPLOY.md](README_DEPLOY.md).

### 2. Start the Backend

From the project root:

```powershell
.\.dwndss\Scripts\Activate.ps1
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation: http://127.0.0.1:8000/docs

### 3. Start the Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the application at http://localhost:5173/.

## Notes

- Ensure the BigQuery Data Warehouse is populated before using the application.
- Run the backend and frontend simultaneously.
- Update the API URL and BigQuery configuration when using a different environment.