# ============================================================
# EIA Draft Copilot — 백엔드 Docker 이미지
# Python 3.12 + FastAPI + PostGIS 클라이언트 + 공간 분석 라이브러리
# ============================================================

FROM python:3.12-slim AS base

# 시스템 의존성: GDAL, GEOS, PROJ (geopandas/shapely/pyproj 빌드 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gdal-bin \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐싱 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# matplotlib 폰트 캐시 사전 빌드
RUN python -c "import matplotlib; matplotlib.use('Agg')" 2>/dev/null || true

EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 엔트리포인트: Alembic 마이그레이션 후 uvicorn 실행
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
