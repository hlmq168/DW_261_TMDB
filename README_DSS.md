TMDB Movie Investment Decision Support System (TMDB DSS)
A Python-based Decision Support System (DSS) for exploring movie-market
opportunities and supporting preliminary investment analysis using
TMDB-derived data stored in Google BigQuery.
Project status: Development / baseline implementation. Some
modules have been executed individually, but full end-to-end
integration and comprehensive testing are still pending. Results
should be treated as decision-support signals, not investment
guarantees.

1. Project objectives
The system is designed to help users:
- Analyze historical genre performance and market-share trends.
- Estimate relative genre potential using market size, market growth,
  and weighted ratings.
- Identify currently popular movies.
- Filter movie candidates using a maximum budget and other
  constraints.
- Rank candidates according to an investment objective.
- Provide a common service interface for downstream applications.
The DSS is an analytical prototype. TMDB budget and revenue fields may
be incomplete or inaccurate and do not necessarily represent production
costs, distribution costs, net profit, or an investor's actual return.
2. Main capabilities
  Component                           Responsibility
  Business metrics                    Provides movie-level business and
rating metrics from the data
warehouse.

  Genre trend                         Analyzes historical genre-level
metrics and changes over time.

  Genre potential                     Produces relative potential scores
for genres.

  Trending movies                     Ranks movies by popularity within
the available snapshot and applies
vote/genre filters.

  Budget filtering                    Filters candidate movies using
budget, genre, release year,
rating, and vote constraints.

  Investment ranking                  Scores and ranks candidates using
the selected objective.

  Recommendation                      Contains content-based and hybrid
recommendation modules.

  Decision Engine                     Orchestrates market analysis,
candidate filtering, and investment
ranking.

  Service interface                   Exposes analyze_investment() as
the main entry point.
Output normalization                Converts results into
JSON-compatible Python values.
Investment objectives
The baseline ranking implementation supports these objective names:
- BALANCED
- HIGH_ROI
- HIGH_PROFIT
- POPULARITY
- LOW_RISK
The score weights and proxy variables are analytical assumptions, not
statistically validated investment models. In particular, vote count is
only a proxy for public attention/data support, not a complete measure
of investment risk.
3. Architecture
TMDB source data
      |
      v
Google BigQuery Data Warehouse
      |
      v
Data loaders and business metrics
      |
      +--------------------+
      |                    |
      v                    v
Analytics              Recommendation
- Genre trends         - Content-based
- Genre potential      - Hybrid
- Trending movies
      |                    |
      +----------+---------+
                 |
                 v
             Decision
       - Budget filtering
       - Investment ranking
       - Investment strategy
                 |
                 v
           Decision Engine
                 |
                 v
              Service
                 |
                 v
       Standardized DSS output
4. Project structure
The project uses a src layout:
DW_261_TMDB/
├── src/
│   └── tmdb_dss/
│       ├── analytics/
│       │   ├── genre_trend.py
│       │   ├── genre_prediction.py
│       │   └── trending.py
│       ├── decision/
│       │   ├── budget_filter.py
│       │   ├── investment_ranking.py
│       │   ├── investment_strategy.py
│       │   └── decision_engine.py
│       ├── recommendation/
│       │   ├── content_based.py
│       │   └── hybrid.py
│       ├── metrics/
│       │   └── business_metrics.py
│       ├── config.py
│       ├── connection.py
│       ├── data_loader.py
│       ├── output.py
│       ├── service.py
│       └── __init__.py
├── tests/
├── README.md
├── requirements.txt
├── pyproject.toml
└── .gitignore
Some modules or test files may be added, renamed, or removed as
implementation progresses. Keep this tree synchronized with the actual
repository before release.
5. Requirements
- Python 3.10 or later (Python 3.11 is recommended for a newer
  runtime).
- Access to the Google Cloud project and BigQuery dataset used by the
  TMDB data warehouse.
- Google Cloud credentials with permission to create BigQuery jobs and
  read the required datasets/tables/views.
- Python dependencies listed in requirements.txt.
The project has been developed in a Windows environment using a virtual
environment.
6. Installation
Open a terminal in the project root directory.
6.1 Create and activate a virtual environment
Windows CMD:
python -m venv .venv
.venv\Scripts\activate
6.2 Install dependencies
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
6.3 Install the project in editable mode
The project root must contain pyproject.toml.
pip install -e .
Editable installation makes the package importable as tmdb_dss while
allowing source changes to take effect without reinstalling.
7. Google Cloud BigQuery configuration
The DSS reads analytical data from BigQuery. Configure Google Cloud
authentication before running it.

A common local development approach is Application Default Credentials:
gcloud auth application-default login
The Google account must have access to the relevant BigQuery project and
dataset.

The project configuration is defined in src/tmdb_dss/config.py. Check
that file and set the project/dataset values to match the actual
warehouse configuration. In the current project context, the dataset has
been referred to as:
dsstmdb.tmdbdw
Do not commit service-account JSON keys, access tokens, private keys, or
other credentials to source control. If the project uses a
service-account key instead of Application Default Credentials, keep the
key outside the repository and configure its path securely.
8. Basic usage
After installing the package, import the public service function:
from tmdb_dss import analyze_investment

result = analyze_investment(
    budget=50_000_000,
    genres=["Action", "Drama"],
    objective="BALANCED",
    min_votes=100,
    top_n=20
)

print(result)
The budget value is expressed in the same currency units as the
warehouse budget field. Confirm the warehouse currency before
interpreting or comparing values.
Parameters
  Parameter               Type                    Description
  budget                number                  Maximum movie budget
used by the candidate
filter.

  genres                string, list, or None Optional target genre
or list of genres. When
omitted, the Decision
Engine selects genres
from the
genre-potential
results.

  objective             string                  Ranking objective:
BALANCED, HIGH_ROI,
HIGH_PROFIT,
POPULARITY, or
LOW_RISK.

  min_votes             integer                 Minimum vote count used
by relevant movie
filters.
top_n                 integer                 Maximum number of
ranked candidates
returned.
Example using one genre:
result = analyze_investment(
    budget=20_000_000,
    genres="Action",
    objective="POPULARITY",
    top_n=10
)
9. Output structure
The standardized output is intended to be a JSON-compatible Python
dictionary with the following top-level sections:
result
├── metadata
├── input
├── market_analysis
│   ├── genre_trends
│   ├── genre_potential
│   └── trending_movies
├── investment_analysis
│   ├── candidate_count
│   ├── ranking_method
│   └── ranking
└── summary
    ├── recommended_movie_count
    ├── top_recommendations
    └── warnings
To serialize the result as JSON:
import json

with open("investment_result.json", "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=4)
The exact fields within each movie record depend on the columns returned
by the relevant BigQuery views and analytics modules.
10. Running modules
Run package modules from the project root with python -m so that
package-relative imports work.

Examples:
python -m src.tmdb_dss.analytics.genre_trend
python -m src.tmdb_dss.analytics.genre_prediction
python -m src.tmdb_dss.analytics.trending
Use the actual module entry points available in the checked-out project.
Not every module necessarily defines a command-line entry point.
11. Data and analytical limitations
1. Incomplete financial coverage: TMDB budget and revenue fields
   are missing for many movies. Financial rankings may therefore
   operate on a much smaller subset than general popularity or rating
   analysis.
2. ROI interpretation: roi_percent based on revenue and
   production budget is not net profit, cash-on-cash return, or an
   investor's realized return. It excludes many costs and financing
   arrangements.
3. Financial eligibility: Use the warehouse's usable_for_roi flag
   and non-null ROI values when interpreting ROI-based rankings. Do not
   infer ROI eligibility from has_financials alone.
4. Recent release years: Recent years may be incomplete and should
   not be compared directly with mature historical years without
   accounting for coverage.
5. Genre potential: Scores are relative to the genres and period
   included in the calculation. They are not probabilities of
   commercial success.
6. Trending interpretation: A single popularity snapshot supports
   relative popularity ranking, not true time-series trend detection.
   Detecting emerging trends requires historical snapshots.
7. Risk proxy: Vote count and rating are incomplete proxies. They
   do not replace a financial, production, market, or portfolio risk
   assessment.
8. Recommendation quality: Content-based and hybrid recommendation
   quality depends on the coverage and correctness of movie metadata
   and the final integration of those modules.
12. Testing status
Some analytical and decision modules have been run individually during
development, including genre trend, genre potential, trending movies,
budget filtering, and selected investment-ranking objectives.

A comprehensive end-to-end test suite, full objective coverage,
recommendation evaluation, and packaging verification should be
completed before treating the project as a production-ready system.

Suggested future checks:
- Verify BigQuery connectivity and required views.
- Test filters with missing, zero, and boundary budget values.
- Test all investment objectives.
- Verify output serialization for null, NumPy, and pandas values.
- Evaluate content-based and hybrid recommendation quality.
- Run the complete Decision Engine through the public service
  interface.
- Build and install the package in a clean environment.
13. Security and version control
The repository should not contain:
- .venv/, .dwndss/, or other virtual environments.
- Google Cloud service-account keys or credential files.
- .env files containing secrets.
- Local caches, temporary exports, or large generated datasets.
A typical .gitignore should include:
.venv/
.dwndss/
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.env
*.json
.pytest_cache/
If the project needs to version-control non-secret JSON configuration
files, replace the broad *.json rule with a narrower rule that
excludes only credential files.
14. Future improvements
- Complete integration and automated testing.
- Validate ranking weights against historical outcomes.
- Improve financial data-quality checks and coverage reporting.
- Add historical popularity snapshots for genuine trend detection.
- Evaluate recommendation precision and ranking metrics.
- Add model explainability and confidence/coverage indicators.
- Add a dashboard or API after the core DSS is stable.