# TMDB Movie Investment Decision Support System (TMDB DSS)

A Python-based Decision Support System (DSS) for exploring movie-market opportunities and supporting preliminary investment analysis using TMDB-derived data stored in Google BigQuery.

> **Project status:** Development / baseline implementation. Some modules have been executed individually, but full end-to-end integration and comprehensive testing are still pending. Results should be treated as decision-support signals, not investment guarantees.

---

## 1. Project Objectives

The system is designed to help users:
- Analyze historical genre performance and market-share trends.
- Estimate relative genre potential using market size, market growth, and weighted ratings.
- Identify currently popular movies.
- Filter movie candidates using a maximum budget and other constraints.
- Rank candidates according to an investment objective.
- Provide a common service interface for downstream applications.

> **Disclaimer:** The DSS is an analytical prototype. TMDB budget and revenue fields may be incomplete or inaccurate and do not necessarily represent production costs, distribution costs, net profit, or an investor's actual return.

---

## 2. Main Capabilities

| Component | Responsibility |
| :--- | :--- |
| **Business metrics** | Provides movie-level business and rating metrics from the data warehouse. |
| **Genre trend** | Analyzes historical genre-level metrics and changes over time. |
| **Genre potential** | Produces relative potential scores for genres. |
| **Trending movies** | Ranks movies by popularity within the available snapshot and applies vote/genre filters. |
| **Budget filtering** | Filters candidate movies using budget, genre, release year, rating, and vote constraints. |
| **Investment ranking** | Scores and ranks candidates using the selected objective. |
| **Recommendation** | Contains content-based and hybrid recommendation modules. |
| **Decision Engine** | Orchestrates market analysis, candidate filtering, and investment ranking. |
| **Service interface** | Exposes `analyze_investment()` as the main entry point. |
| **Output normalization** | Converts results into JSON-compatible Python values. |

### Investment Objectives
The baseline ranking implementation supports these objective names:
- `BALANCED`
- `HIGH_ROI`
- `HIGH_PROFIT`
- `POPULARITY`
- `LOW_RISK`

> **Note:** The score weights and proxy variables are analytical assumptions, not statistically validated investment models. In particular, vote count is only a proxy for public attention/data support, not a complete measure of investment risk.

---

## 3. Architecture

```text
TMDB source data
      │
      ▼
Google BigQuery Data Warehouse (`dsstmdb.tmdbdw`)
      │
      ▼
Data loaders and business metrics
      │
      ├────────────────────┐
      ▼                    ▼
Analytics              Recommendation
- Genre trends         - Content-based
- Genre potential      - Hybrid
- Trending movies
      │                    │
      └──────────┬─────────┘
                 │
                 ▼
             Decision
       - Budget filtering
       - Investment ranking
       - Investment strategy
                 │
                 ▼
          Decision Engine
                 │
                 ▼
              Service
                 │
                 ▼
       Standardized DSS output
**
