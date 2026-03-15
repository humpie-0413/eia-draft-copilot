#!/bin/bash
set -e

echo "=== EIA Draft Copilot 백엔드 시작 ==="

# DB 연결 대기
echo "PostgreSQL 연결 대기 중..."
until python -c "
import psycopg2, os
url = os.environ.get('DATABASE_URL', '').replace('+asyncpg', '')
conn = psycopg2.connect(url)
conn.close()
print('PostgreSQL 연결 성공')
" 2>/dev/null; do
    echo "  DB 대기 중... 3초 후 재시도"
    sleep 3
done

# Alembic 마이그레이션 실행
echo "Alembic 마이그레이션 실행..."
alembic upgrade head
echo "마이그레이션 완료"

# 메인 프로세스 실행
echo "서버 시작: $@"
exec "$@"
