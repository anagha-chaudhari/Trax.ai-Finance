from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.config import settings
from models.database import create_tables
from routers import auth, analysis, portfolio

app = FastAPI(title=settings.app_name, description="Multi-Agent AI stock analysis platform",
              version="1.0.0", docs_url="/docs", redoc="/redoc",)

app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5500","http://localhost:5500", "http://localhost", "http://127.0.0.1"],
    allow_credentials=True,  # allow cookies and auth headers
    allow_methods=["*"],   # allow GET, POST, PUT, DELETE etc.
    allow_headers=["*"],       # allow Authorization header etc.
)


@app.on_event("startup")
def on_startup():
    create_tables()
    print(f"=>:{settings.app_name} started")
    print(f"Docs available at http://localhost:8000/docs")

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])

app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": settings.app_name}