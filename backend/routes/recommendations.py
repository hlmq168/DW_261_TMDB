import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.tmdb_dss.service import get_movie_recommendations

router = APIRouter(
    prefix="/api/recommendations",
    tags=["Recommendations"],
)


class RecommendationRequest(BaseModel):
    movie_id: int = Field(gt=0)


@router.post("/")
def recommend_movies(request: RecommendationRequest):
    try:
        results = get_movie_recommendations(
            movie_id=request.movie_id,
            top_n=100,
            content_weight=0.50,
            rating_weight=0.30,
            business_weight=0.20,
        )

        if results.empty:
            return {
                "source_movie_id": request.movie_id,
                "total": 0,
                "results": [],
            }

        top_results = results.head(10)

        # Convert pandas/numpy values and missing values
        # into JSON-compatible values.
        records = json.loads(
            top_results.to_json(
                orient="records",
                date_format="iso",
            )
        )

        return {
            "source_movie_id": request.movie_id,
            "total": len(records),
            "results": records,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {str(exc)}",
        )