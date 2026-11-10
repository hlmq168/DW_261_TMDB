from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.movies import router as movies_router
from backend.routes.recommendations import router as recommendations_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.investment import router as investment_router

app = FastAPI(
    title="TMDB DSS API",
    description="Backend API for the TMDB Decision Support System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies_router)
app.include_router(recommendations_router)
app.include_router(dashboard_router)
app.include_router(investment_router)