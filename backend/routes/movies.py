from fastapi import APIRouter, HTTPException, Query

from tmdb_dss.data_loader import load_recommendation_movies

router = APIRouter(prefix="/api/movies", tags=["Movies"])


@router.get("/search")
def search_movies(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    try:
        movies = load_recommendation_movies()

        matching_movies = movies[
            movies["title"].str.contains(
                q.strip(),
                case=False,
                na=False,
                regex=False,
            )
        ].drop_duplicates(subset=["id"])

        total = len(matching_movies)

        results = matching_movies.iloc[offset:offset + limit]

        results = results.astype(object).where(
            results.notna(), None
        )

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": results.to_dict(orient="records"),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )