from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.optimizer import router as optimizer_router
from app.core.config import get_settings
from app.db.session import engine, SessionLocal, init_db

app = FastAPI(title="SQL Optimizer API")
settings = get_settings()

# CORS (allow React frontend origin in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # or ["http://localhost:5173"] for strict mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(optimizer_router, prefix="/api/v1")

# Optional: create DB tables (for quickstart; in prod use migrations)
@app.on_event("startup")
def on_startup():
    init_db()
