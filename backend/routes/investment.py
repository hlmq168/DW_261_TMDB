from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from functools import lru_cache

from tmdb_dss.data_loader import load_content_features
from tmdb_dss.decision.decision_engine import (
    run_investment_analysis,
)


router = APIRouter(
    prefix="/api/investment",
    tags=["Investment"],
)


class InvestmentRequest(BaseModel):
    budget: float = Field(gt=0)
    genres: list[str] | None = None
    objective: Literal[
        "BALANCED",
        "HIGH_ROI",
        "HIGH_PROFIT",
        "POPULARITY",
        "LOW_RISK",
    ] = "BALANCED"
    min_votes: int = Field(default=100, ge=0)
    top_n: int = Field(default=20, ge=5, le=50)


@router.post("/analyze")
def analyze_investment(request: InvestmentRequest):

    try:
        result = run_investment_analysis(
            budget=request.budget,
            genres=request.genres,
            objective=request.objective,
            min_votes=request.min_votes,
            top_n=request.top_n,
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

@lru_cache(maxsize=1)
def get_available_genres():
    genre_df = load_content_features()["genres"]

    genres = genre_df["genre_name"].dropna().astype(str).str.strip()

    return sorted(
        {
            genre
            for genre in genres
            if genre and genre.casefold() != "unknown"
        },
        key=str.casefold,
    )


@router.get("/genres")
def get_genres():
    return {"genres": get_available_genres()}