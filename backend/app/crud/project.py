import uuid

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape as shapely_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def _geojson_to_wkb(geojson_geom) -> str | None:
    """GeoJSON geometry dict → WKB element for PostGIS."""
    if geojson_geom is None:
        return None
    geom_dict = geojson_geom.model_dump()
    shp = shapely_shape(geom_dict)
    return from_shape(shp, srid=4326)


def _wkb_to_geojson(wkb_element) -> dict | None:
    """WKB element from PostGIS → GeoJSON-compatible dict."""
    if wkb_element is None:
        return None
    shp = to_shape(wkb_element)
    return shp.__geo_interface__


async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    project = Project(
        name=data.name,
        description=data.description,
        project_type=data.project_type.value if data.project_type else None,
        geometry=_geojson_to_wkb(data.geometry),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def list_projects(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> tuple[list[Project], int]:
    # 전체 건수
    count_result = await db.execute(select(func.count()).select_from(Project))
    total = count_result.scalar_one()

    # 목록
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit)
    )
    projects = list(result.scalars().all())
    return projects, total


async def update_project(
    db: AsyncSession, project: Project, data: ProjectUpdate
) -> Project:
    update_data = data.model_dump(exclude_unset=True)

    if "geometry" in update_data:
        update_data["geometry"] = _geojson_to_wkb(data.geometry)

    if "project_type" in update_data and update_data["project_type"] is not None:
        update_data["project_type"] = update_data["project_type"].value

    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()
