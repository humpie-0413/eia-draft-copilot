import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate


async def create_data_source(db: AsyncSession, data: DataSourceCreate) -> DataSource:
    source = DataSource(
        name=data.name,
        connector_key=data.connector_key,
        base_url=data.base_url,
        description=data.description,
        enabled=data.enabled,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def get_data_source(db: AsyncSession, source_id: uuid.UUID) -> DataSource | None:
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    return result.scalar_one_or_none()


async def get_data_source_by_key(db: AsyncSession, connector_key: str) -> DataSource | None:
    """커넥터 키로 데이터 소스를 조회한다."""
    result = await db.execute(
        select(DataSource).where(DataSource.connector_key == connector_key)
    )
    return result.scalar_one_or_none()


async def list_data_sources(
    db: AsyncSession, skip: int = 0, limit: int = 50, enabled_only: bool = False
) -> tuple[list[DataSource], int]:
    query = select(DataSource)
    count_query = select(func.count()).select_from(DataSource)

    if enabled_only:
        query = query.where(DataSource.enabled.is_(True))
        count_query = count_query.where(DataSource.enabled.is_(True))

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(DataSource.name).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def update_data_source(
    db: AsyncSession, source: DataSource, data: DataSourceUpdate
) -> DataSource:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


async def delete_data_source(db: AsyncSession, source: DataSource) -> None:
    await db.delete(source)
    await db.commit()
