from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.data_sources import router as data_sources_router
from app.api.v1.evidences import router as evidences_router
from app.api.v1.projects import router as projects_router
from app.api.v1.similar_cases import router as similar_cases_router
from app.api.v1.snapshots import router as snapshots_router
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — 개발 시 Next.js 프론트엔드 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 라우터 등록
app.include_router(projects_router, prefix="/api/v1")
app.include_router(data_sources_router, prefix="/api/v1")
app.include_router(evidences_router, prefix="/api/v1")
app.include_router(snapshots_router, prefix="/api/v1")
app.include_router(similar_cases_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
