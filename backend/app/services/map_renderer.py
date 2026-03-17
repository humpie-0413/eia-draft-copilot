"""정적 도면 렌더링 서비스 — matplotlib 기반.

사업 경계, 버퍼, 측정소, 예측 결과 등을 조합하여
환경영향평가서용 정적 도면(PNG)을 생성한다.

도면 종류:
1. 사업대상지 위치도 (location)
2. 토지이용현황도 (land_use)
3. 환경측정소 분포도 (monitoring_stations)
4. 소음 예측 등고선도 (noise_contour)
5. 대기확산 예측도 (air_dispersion)
"""

from __future__ import annotations

import io
import math
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 비대화형 백엔드

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape

from geoalchemy2.shape import to_shape

from app.services.spatial_analysis import (
    compute_buffer,
    OverlayItem,
    _haversine_distance,
)

# ── 한글 폰트 설정 ──

_FONT_CONFIGURED = False


def _configure_korean_font():
    """matplotlib에 한글 폰트를 등록한다."""
    global _FONT_CONFIGURED
    if _FONT_CONFIGURED:
        return

    import matplotlib.font_manager as fm

    font_candidates = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothic.ttf",
    ]

    for font_path in font_candidates:
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            prop = fm.FontProperties(fname=font_path)
            plt.rcParams["font.family"] = prop.get_name()
            break
    else:
        # 폰트 못 찾으면 기본 sans-serif 사용
        plt.rcParams["font.family"] = "sans-serif"

    plt.rcParams["axes.unicode_minus"] = False
    _FONT_CONFIGURED = True


# ── 공통 상수 ──

DPI = 150
FIGSIZE = (11.69, 8.27)  # A4 가로 (인치)

# 용도지역별 색상
LAND_USE_COLORS: dict[str, str] = {
    "주거지역": "#FFE066",
    "상업지역": "#FF6B6B",
    "공업지역": "#CC5DE8",
    "녹지지역": "#51CF66",
    "관리지역": "#74C0FC",
    "농림지역": "#A9E34B",
    "자연환경보전지역": "#20C997",
}
LAND_USE_DEFAULT_COLOR = "#CED4DA"


# ── 도면 종류 정의 ──

MAP_TYPES = {
    "location": "사업대상지 위치도",
    "land_use": "토지이용현황도",
    "monitoring_stations": "환경측정소 분포도",
    "noise_contour": "소음 예측 등고선도",
    "air_dispersion": "대기오염물질 확산 예측도",
}


@dataclass
class MapRenderContext:
    """도면 렌더링에 필요한 데이터 컨텍스트."""

    project_id: str
    project_name: str
    geometry_wkb: object | None = None   # PostGIS WKB
    centroid: tuple[float, float] | None = None  # (lat, lon)
    overlay_items: list[OverlayItem] = field(default_factory=list)
    land_use_data: list[dict] = field(default_factory=list)
    prediction_result: object | None = None   # PredictionResult
    output_dir: str | None = None


def _get_output_path(ctx: MapRenderContext, map_type: str) -> Path:
    """도면 출력 경로를 반환한다."""
    base = Path(ctx.output_dir) if ctx.output_dir else Path("output/maps")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{ctx.project_id}_{map_type}.png"


def _add_north_arrow(ax, x=0.95, y=0.95):
    """방위표(북쪽 화살표)를 추가한다."""
    ax.annotate(
        "N", xy=(x, y), xycoords="axes fraction",
        fontsize=14, fontweight="bold", ha="center", va="center",
    )
    ax.annotate(
        "", xy=(x, y - 0.01), xycoords="axes fraction",
        xytext=(x, y - 0.06), textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", lw=2, color="black"),
    )


def _add_scalebar(ax, geom_4326, map_width_deg: float):
    """축척을 추가한다."""
    center_lat = geom_4326.centroid.y
    # 1도 경도 ≈ 111km * cos(lat)
    deg_to_km = 111.0 * math.cos(math.radians(center_lat))
    map_width_km = map_width_deg * deg_to_km

    # 축척 바 길이 결정 (지도 폭의 약 20%)
    target_km = map_width_km * 0.2
    # 깔끔한 숫자로 반올림
    nice_values = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50]
    bar_km = min(nice_values, key=lambda v: abs(v - target_km))
    bar_deg = bar_km / deg_to_km

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x0 = xlim[0] + (xlim[1] - xlim[0]) * 0.05
    y0 = ylim[0] + (ylim[1] - ylim[0]) * 0.05

    ax.plot([x0, x0 + bar_deg], [y0, y0], "k-", linewidth=3)
    ax.plot([x0, x0], [y0 - (ylim[1] - ylim[0]) * 0.005, y0 + (ylim[1] - ylim[0]) * 0.005], "k-", linewidth=2)
    ax.plot([x0 + bar_deg, x0 + bar_deg], [y0 - (ylim[1] - ylim[0]) * 0.005, y0 + (ylim[1] - ylim[0]) * 0.005], "k-", linewidth=2)

    label = f"{bar_km:g} km" if bar_km >= 1 else f"{bar_km * 1000:g} m"
    ax.text(x0 + bar_deg / 2, y0 + (ylim[1] - ylim[0]) * 0.015, label,
            ha="center", va="bottom", fontsize=9, fontweight="bold")


def _plot_boundary(ax, geom, color="green", label="사업 경계"):
    """사업 경계 Polygon을 플롯한다."""

    if isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    elif isinstance(geom, Polygon):
        polygons = [geom]
    else:
        return

    for i, poly in enumerate(polygons):
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, alpha=0.3, fc=color, ec=color, linewidth=2,
                label=label if i == 0 else None)


def _plot_buffer(ax, geom_wkb, radius_m, color, linestyle, label):
    """버퍼 원을 플롯한다."""
    buf = compute_buffer(geom_wkb, radius_m)
    if buf is None:
        return None

    buf_shape = shape(buf.buffer_geojson)

    polys = list(buf_shape.geoms) if isinstance(buf_shape, MultiPolygon) else [buf_shape]
    for i, poly in enumerate(polys):
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color=color, linestyle=linestyle, linewidth=1.5,
                label=label if i == 0 else None)

    return buf_shape


# ═══════════════════════════════════════════════════════════════
# 1. 사업대상지 위치도
# ═══════════════════════════════════════════════════════════════

def render_location_map(ctx: MapRenderContext) -> bytes | None:
    """사업대상지 위치도를 렌더링한다.

    - 사업 경계 (초록색 채우기)
    - 1km 버퍼 (파란 점선)
    - 5km 버퍼 (보라 점선)
    - 버퍼 내 측정소/문화재 마커
    - 범례, 축척, 방위표
    """
    _configure_korean_font()

    if ctx.geometry_wkb is None:
        return None

    geom = to_shape(ctx.geometry_wkb)

    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE, dpi=DPI)
    ax.set_title("사업대상지 위치도", fontsize=18, fontweight="bold", pad=15)
    ax.set_xlabel("경도 (°E)", fontsize=10)
    ax.set_ylabel("위도 (°N)", fontsize=10)

    # 사업 경계
    _plot_boundary(ax, geom, color="#2E8B57", label="사업 경계")

    # 1km / 5km 버퍼
    buf_5km = _plot_buffer(ax, ctx.geometry_wkb, 5000, "#8B5CF6", "--", "5km 버퍼")
    buf_1km = _plot_buffer(ax, ctx.geometry_wkb, 1000, "#3B82F6", "--", "1km 버퍼")

    # 범위 설정 (5km 버퍼 기준)
    if buf_5km:
        minx, miny, maxx, maxy = buf_5km.bounds
        pad = (maxx - minx) * 0.1
        ax.set_xlim(minx - pad, maxx + pad)
        ax.set_ylim(miny - pad, maxy + pad)
        map_width = maxx - minx + 2 * pad
    else:
        minx, miny, maxx, maxy = geom.bounds
        pad = max(maxx - minx, maxy - miny) * 0.5
        ax.set_xlim(minx - pad, maxx + pad)
        ax.set_ylim(miny - pad, maxy + pad)
        map_width = maxx - minx + 2 * pad

    # 오버레이 항목 플롯
    _plot_overlay_markers(ax, ctx.overlay_items)

    # 범례, 축척, 방위표
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    _add_north_arrow(ax)
    _add_scalebar(ax, geom, map_width)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linestyle=":")

    # 부제: 사업명
    fig.text(0.5, 0.01, f"사업명: {ctx.project_name}", ha="center", fontsize=9,
             color="gray")

    plt.tight_layout(rect=[0, 0.03, 1, 1])

    return _fig_to_bytes(fig)


def _plot_overlay_markers(ax, items: list[OverlayItem]):
    """오버레이 항목을 마커로 플롯한다."""
    plotted_types: set[str] = set()

    for item in items:
        marker_style = _get_marker_style(item.item_type)
        label = item.item_type if item.item_type not in plotted_types else None
        plotted_types.add(item.item_type)

        ax.plot(item.lon, item.lat,
                marker=marker_style["marker"],
                color=marker_style["color"],
                markersize=marker_style["size"],
                label=label,
                zorder=5)

        # 라벨 표시 (이름이 있는 경우)
        if item.name:
            display_name = item.name[:10] + "…" if len(item.name) > 10 else item.name
            ax.annotate(
                display_name,
                (item.lon, item.lat),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=7,
                color=marker_style["color"],
                alpha=0.8,
            )


def _get_marker_style(item_type: str) -> dict:
    """항목 유형에 따른 마커 스타일을 반환한다."""
    styles = {
        "대기측정소": {"marker": "^", "color": "#EF4444", "size": 10},
        "수질측정소": {"marker": "o", "color": "#3B82F6", "size": 9},
        "소음측정소": {"marker": "s", "color": "#F59E0B", "size": 9},
        "문화재": {"marker": "*", "color": "#EF4444", "size": 12},
        "생태조사지점": {"marker": "D", "color": "#10B981", "size": 8},
        "토양측정소": {"marker": "p", "color": "#8B5CF6", "size": 9},
    }
    return styles.get(item_type, {"marker": "x", "color": "#6B7280", "size": 8})


# ═══════════════════════════════════════════════════════════════
# 2. 토지이용현황도
# ═══════════════════════════════════════════════════════════════

def render_land_use_map(ctx: MapRenderContext) -> bytes | None:
    """토지이용현황도를 렌더링한다."""
    _configure_korean_font()

    if ctx.geometry_wkb is None:
        return None

    geom = to_shape(ctx.geometry_wkb)

    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE, dpi=DPI)
    ax.set_title("토지이용현황도", fontsize=18, fontweight="bold", pad=15)
    ax.set_xlabel("경도 (°E)", fontsize=10)
    ax.set_ylabel("위도 (°N)", fontsize=10)

    # 범위 설정 (사업 경계 + 1km 여유)
    buf_1km = compute_buffer(ctx.geometry_wkb, 1000)
    if buf_1km:
        buf_shape = shape(buf_1km.buffer_geojson)
        minx, miny, maxx, maxy = buf_shape.bounds
        pad = (maxx - minx) * 0.1
    else:
        minx, miny, maxx, maxy = geom.bounds
        pad = max(maxx - minx, maxy - miny) * 0.3

    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)

    # 토지이용 데이터가 있으면 색상 구분
    legend_patches = []
    if ctx.land_use_data:
        for lu_item in ctx.land_use_data:
            zone_name = lu_item.get("zone_name", "기타")
            color = _get_land_use_color(zone_name)

            if "geometry" in lu_item:
                try:
                    lu_geom = shape(lu_item["geometry"])
                    polys = list(lu_geom.geoms) if isinstance(lu_geom, MultiPolygon) else [lu_geom]
                    for poly in polys:
                        xs, ys = poly.exterior.xy
                        ax.fill(xs, ys, alpha=0.5, fc=color, ec=color, linewidth=0.5)
                except Exception:
                    pass
            else:
                # geometry 없는 경우: 중심점 근처에 텍스트 라벨만
                if "lat" in lu_item and "lon" in lu_item:
                    ax.annotate(
                        zone_name, (lu_item["lon"], lu_item["lat"]),
                        fontsize=8, ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.3", fc=color, alpha=0.7),
                    )

            if zone_name not in {p.get_label() for p in legend_patches}:
                legend_patches.append(
                    mpatches.Patch(color=color, alpha=0.6, label=zone_name)
                )
    else:
        # 데이터 없음 안내
        cx, cy = geom.centroid.x, geom.centroid.y
        ax.text(cx, cy, "토지이용 데이터 미수집", ha="center", va="center",
                fontsize=12, color="gray", style="italic")

    # 사업 경계 (흰 점선)
    _plot_boundary(ax, geom, color="white", label="사업 경계")
    # 외곽선만 다시
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    for poly in polys:
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, "w--", linewidth=2.5)
        ax.plot(xs, ys, "k-", linewidth=1.0)

    if legend_patches:
        ax.legend(handles=legend_patches, loc="upper left", fontsize=8, framealpha=0.9)

    _add_north_arrow(ax)
    map_width = (maxx + pad) - (minx - pad)
    _add_scalebar(ax, geom, map_width)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2, linestyle=":")

    fig.text(0.5, 0.01, f"사업명: {ctx.project_name}", ha="center", fontsize=9,
             color="gray")
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    return _fig_to_bytes(fig)


def _get_land_use_color(zone_name: str) -> str:
    """용도지역명에서 색상을 추출한다."""
    for key, color in LAND_USE_COLORS.items():
        if key in zone_name:
            return color
    return LAND_USE_DEFAULT_COLOR


# ═══════════════════════════════════════════════════════════════
# 3. 환경측정소 분포도
# ═══════════════════════════════════════════════════════════════

def render_monitoring_stations_map(ctx: MapRenderContext) -> bytes | None:
    """환경측정소 분포도를 렌더링한다."""
    _configure_korean_font()

    if ctx.geometry_wkb is None:
        return None

    geom = to_shape(ctx.geometry_wkb)

    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE, dpi=DPI)
    ax.set_title("환경측정소 분포도", fontsize=18, fontweight="bold", pad=15)
    ax.set_xlabel("경도 (°E)", fontsize=10)
    ax.set_ylabel("위도 (°N)", fontsize=10)

    # 사업 경계 + 1km 버퍼
    _plot_boundary(ax, geom, color="#2E8B57", label="사업 경계")
    _plot_buffer(ax, ctx.geometry_wkb, 1000, "#3B82F6", "--", "1km 버퍼")

    # 측정소 분류별 플롯
    air_stations = [i for i in ctx.overlay_items if i.item_type == "대기측정소"]
    water_stations = [i for i in ctx.overlay_items if i.item_type == "수질측정소"]
    noise_stations = [i for i in ctx.overlay_items if i.item_type == "소음측정소"]
    other_stations = [
        i for i in ctx.overlay_items
        if i.item_type not in ("대기측정소", "수질측정소", "소음측정소", "문화재")
    ]

    # 대기측정소 (빨간 삼각형)
    for i, st in enumerate(air_stations):
        ax.plot(st.lon, st.lat, "^", color="#EF4444", markersize=12, zorder=5,
                label="대기측정소" if i == 0 else None)
        _annotate_station(ax, st)

    # 수질측정소 (파란 원)
    for i, st in enumerate(water_stations):
        ax.plot(st.lon, st.lat, "o", color="#3B82F6", markersize=10, zorder=5,
                label="수질측정소" if i == 0 else None)
        _annotate_station(ax, st)

    # 소음측정소 (노란 사각형)
    for i, st in enumerate(noise_stations):
        ax.plot(st.lon, st.lat, "s", color="#F59E0B", markersize=10, zorder=5,
                label="소음측정소" if i == 0 else None)
        _annotate_station(ax, st)

    # 기타
    for i, st in enumerate(other_stations):
        ax.plot(st.lon, st.lat, "x", color="#6B7280", markersize=8, zorder=5,
                label=st.item_type if i == 0 else None)

    # 범위 설정
    buf_1km = compute_buffer(ctx.geometry_wkb, 1000)
    if buf_1km:
        buf_shape = shape(buf_1km.buffer_geojson)
        minx, miny, maxx, maxy = buf_shape.bounds
        pad = (maxx - minx) * 0.15
    else:
        minx, miny, maxx, maxy = geom.bounds
        pad = max(maxx - minx, maxy - miny) * 0.5

    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)

    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    _add_north_arrow(ax)
    _add_scalebar(ax, geom, (maxx + pad) - (minx - pad))
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linestyle=":")

    fig.text(0.5, 0.01, f"사업명: {ctx.project_name}", ha="center", fontsize=9,
             color="gray")
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    return _fig_to_bytes(fig)


def _annotate_station(ax, station: OverlayItem):
    """측정소 라벨을 표시한다."""
    name = station.name[:12] + "…" if len(station.name) > 12 else station.name
    ax.annotate(
        name, (station.lon, station.lat),
        textcoords="offset points", xytext=(6, 6),
        fontsize=7, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.8),
    )


# ═══════════════════════════════════════════════════════════════
# 4. 소음 예측 등고선도
# ═══════════════════════════════════════════════════════════════

def render_noise_contour_map(ctx: MapRenderContext) -> bytes | None:
    """소음 예측 등고선도를 렌더링한다.

    예측 모델 결과를 동심원 등고선으로 표시한다.
    - 70dB: 빨강
    - 60dB: 주황
    - 55dB(주간기준): 노랑 점선
    - 50dB: 초록
    - 45dB(야간기준): 파랑 점선
    """
    _configure_korean_font()

    if ctx.geometry_wkb is None:
        return None

    geom = to_shape(ctx.geometry_wkb)
    cx, cy = geom.centroid.x, geom.centroid.y

    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE, dpi=DPI)
    ax.set_title("소음 예측 등고선도", fontsize=18, fontweight="bold", pad=15)
    ax.set_xlabel("경도 (°E)", fontsize=10)
    ax.set_ylabel("위도 (°N)", fontsize=10)

    # 소음 예측 데이터 추출
    pr = ctx.prediction_result
    noise_data: list[tuple[float, float]] = []  # (distance_m, dB)

    if pr and hasattr(pr, "predictions"):
        for item in pr.predictions:
            if "주간" in item.pollutant:
                noise_data.append((item.distance_m, item.total_concentration))

    if not noise_data:
        # 기본 데이터 없으면 텍스트만 표시
        ax.text(cx, cy, "소음 예측 데이터 없음", ha="center", va="center",
                fontsize=14, color="gray", style="italic")
        _plot_boundary(ax, geom, color="#2E8B57")
        minx, miny, maxx, maxy = geom.bounds
        pad = max(maxx - minx, maxy - miny) * 1.5
        ax.set_xlim(minx - pad, maxx + pad)
        ax.set_ylim(miny - pad, maxy + pad)
        ax.set_aspect("equal")
        plt.tight_layout()
        return _fig_to_bytes(fig)

    # 최대 거리 + 여유
    max_dist = max(d for d, _ in noise_data) * 1.2
    # 위도 1도 ≈ 111km, 경도 1도 ≈ 111km * cos(lat)
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(cy)))

    # 2D 그리드 생성
    grid_size = 200
    x_range = max_dist * lon_per_m
    y_range = max_dist * lat_per_m

    xs = np.linspace(cx - x_range, cx + x_range, grid_size)
    ys = np.linspace(cy - y_range, cy + y_range, grid_size)
    X, Y = np.meshgrid(xs, ys)

    # 각 그리드 점에서의 소음도 계산 (거리 기반 보간)
    Z = np.zeros_like(X)
    for i in range(grid_size):
        for j in range(grid_size):
            dist = _haversine_distance(cy, cx, Y[i, j], X[i, j])
            Z[i, j] = _interpolate_noise(noise_data, dist)

    # 등고선 레벨 및 색상
    levels = [40, 45, 50, 55, 60, 65, 70, 75, 80]
    cmap = LinearSegmentedColormap.from_list(
        "noise", ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#7C2D12"], N=256
    )

    # 등고면 (채움)
    cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap, alpha=0.5, extend="both")
    plt.colorbar(cf, ax=ax, label="소음도 dB(A)", shrink=0.8)

    # 등고선 (선)
    cs = ax.contour(X, Y, Z, levels=levels, colors="gray", linewidths=0.5, alpha=0.7)
    ax.clabel(cs, inline=True, fontsize=7, fmt="%1.0f dB")

    # 환경기준선 (주간 55dB, 야간 45dB)
    cs_day = ax.contour(X, Y, Z, levels=[55], colors="#F59E0B", linewidths=2, linestyles="--")
    ax.clabel(cs_day, inline=True, fontsize=8, fmt="주간기준 55dB")

    cs_night = ax.contour(X, Y, Z, levels=[45], colors="#3B82F6", linewidths=2, linestyles="--")
    ax.clabel(cs_night, inline=True, fontsize=8, fmt="야간기준 45dB")

    # 사업 경계
    _plot_boundary(ax, geom, color="#2E8B57", label="사업 경계")

    # 음원 위치 표시
    ax.plot(cx, cy, "ro", markersize=10, zorder=10, label="음원 위치")

    # 범위
    ax.set_xlim(cx - x_range * 1.1, cx + x_range * 1.1)
    ax.set_ylim(cy - y_range * 1.1, cy + y_range * 1.1)

    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    _add_north_arrow(ax)
    _add_scalebar(ax, geom, x_range * 2.2)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2, linestyle=":")

    fig.text(0.5, 0.01, f"사업명: {ctx.project_name}", ha="center", fontsize=9,
             color="gray")
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    return _fig_to_bytes(fig)


def _interpolate_noise(data: list[tuple[float, float]], dist: float) -> float:
    """거리 기반으로 소음도를 보간한다."""
    if not data:
        return 0.0

    # 정렬
    sorted_data = sorted(data, key=lambda x: x[0])

    # 범위 외
    if dist <= sorted_data[0][0]:
        return sorted_data[0][1]
    if dist >= sorted_data[-1][0]:
        return sorted_data[-1][1]

    # 선형 보간
    for i in range(len(sorted_data) - 1):
        d0, v0 = sorted_data[i]
        d1, v1 = sorted_data[i + 1]
        if d0 <= dist <= d1:
            ratio = (dist - d0) / (d1 - d0) if d1 != d0 else 0
            return v0 + (v1 - v0) * ratio

    return sorted_data[-1][1]


# ═══════════════════════════════════════════════════════════════
# 5. 대기확산 예측도
# ═══════════════════════════════════════════════════════════════

def render_air_dispersion_map(ctx: MapRenderContext) -> bytes | None:
    """대기오염물질 확산 예측도를 렌더링한다.

    가우시안 플룸 결과를 농도 등고선으로 표시한다.
    환경기준 초과 범위를 빨간 음영으로 표시한다.
    """
    _configure_korean_font()

    if ctx.geometry_wkb is None:
        return None

    geom = to_shape(ctx.geometry_wkb)
    cx, cy = geom.centroid.x, geom.centroid.y

    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE, dpi=DPI)
    ax.set_title("대기오염물질 확산 예측도", fontsize=18, fontweight="bold", pad=15)
    ax.set_xlabel("경도 (°E)", fontsize=10)
    ax.set_ylabel("위도 (°N)", fontsize=10)

    pr = ctx.prediction_result
    air_data: list[tuple[float, float, str, float | None]] = []

    if pr and hasattr(pr, "predictions"):
        # PM10 데이터만 사용 (대표 오염물질)
        for item in pr.predictions:
            if item.pollutant == "PM10":
                air_data.append((
                    item.distance_m,
                    item.total_concentration,
                    item.unit,
                    item.standard_value,
                ))

    if not air_data:
        ax.text(cx, cy, "대기 확산 예측 데이터 없음", ha="center", va="center",
                fontsize=14, color="gray", style="italic")
        _plot_boundary(ax, geom, color="#2E8B57")
        minx, miny, maxx, maxy = geom.bounds
        pad = max(maxx - minx, maxy - miny) * 1.5
        ax.set_xlim(minx - pad, maxx + pad)
        ax.set_ylim(miny - pad, maxy + pad)
        ax.set_aspect("equal")
        plt.tight_layout()
        return _fig_to_bytes(fig)

    max_dist = max(d for d, _, _, _ in air_data) * 1.2
    standard_val = air_data[0][3]  # PM10 환경기준
    unit = air_data[0][2]

    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(cy)))

    # 풍하방향 (동쪽 가정) 편향 그리드
    grid_size = 200
    x_range_down = max_dist * lon_per_m * 1.2   # 풍하방향 (동쪽)
    x_range_up = max_dist * lon_per_m * 0.3      # 풍상방향 (서쪽)
    y_range = max_dist * lat_per_m * 0.6          # 횡방향

    xs = np.linspace(cx - x_range_up, cx + x_range_down, grid_size)
    ys = np.linspace(cy - y_range, cy + y_range, grid_size)
    X, Y = np.meshgrid(xs, ys)

    # 가우시안 플룸: 풍하방향(동쪽) 기준 농도 계산
    Z = np.zeros_like(X)
    bg_conc = 0.0
    if air_data:
        # 가장 먼 거리의 배경 농도 추정
        sorted_air = sorted(air_data, key=lambda x: x[0])
        if len(sorted_air) >= 2:
            # 기여 농도 = total - background 근사
            bg_conc = sorted_air[0][1] - (sorted_air[0][1] - sorted_air[-1][1]) * 0.1

    for i in range(grid_size):
        for j in range(grid_size):
            # 풍하거리(x방향), 횡방향거리(y방향)
            dx_m = (X[i, j] - cx) / lon_per_m
            dy_m = (Y[i, j] - cy) / lat_per_m

            if dx_m <= 0:
                Z[i, j] = bg_conc * 0.5  # 풍상방향은 배경의 절반
                continue

            # 풍하거리에서의 총 농도를 보간
            downwind_dist = math.sqrt(dx_m**2)
            total_at_centerline = _interpolate_air(
                [(d, c) for d, c, _, _ in air_data], downwind_dist
            )

            # 횡방향 가우시안 분포 (σy ≈ 0.15 * x)
            sigma_y = max(0.15 * dx_m, 10.0)
            lateral_factor = math.exp(-(dy_m**2) / (2 * sigma_y**2))
            Z[i, j] = total_at_centerline * lateral_factor

    # 등고선
    max_conc = max(c for _, c, _, _ in air_data) if air_data else 100
    levels = np.linspace(0, max_conc * 1.1, 12)
    levels = levels[levels > 0]

    cmap = LinearSegmentedColormap.from_list(
        "air", ["#E8F5E9", "#FFF9C4", "#FFECB3", "#FFCC02", "#FF9800", "#F44336"], N=256
    )

    cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap, alpha=0.6, extend="both")
    plt.colorbar(cf, ax=ax, label=f"농도 ({unit})", shrink=0.8)

    cs = ax.contour(X, Y, Z, levels=levels, colors="gray", linewidths=0.3, alpha=0.5)
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.1f")

    # 환경기준 초과 범위 (빨간 등고선)
    if standard_val and np.any(Z > standard_val):
        cs_std = ax.contour(X, Y, Z, levels=[standard_val],
                           colors="#EF4444", linewidths=2.5, linestyles="-")
        ax.clabel(cs_std, inline=True, fontsize=9, fmt=f"기준 {standard_val}%s" % unit)
        # 초과 영역 빨간 음영
        ax.contourf(X, Y, Z, levels=[standard_val, Z.max() * 2],
                   colors=["#EF4444"], alpha=0.15)

    # 풍향 화살표
    arrow_x = cx + x_range_down * 0.7
    arrow_y = cy + y_range * 0.8
    ax.annotate(
        "", xy=(arrow_x + x_range_down * 0.15, arrow_y),
        xytext=(arrow_x, arrow_y),
        arrowprops=dict(arrowstyle="-|>", lw=2.5, color="#3B82F6"),
    )
    ax.text(arrow_x + x_range_down * 0.08, arrow_y + y_range * 0.08,
            "풍향", fontsize=10, color="#3B82F6", fontweight="bold")

    # 사업 경계
    _plot_boundary(ax, geom, color="#2E8B57", label="사업 경계")

    # 배출원 위치
    ax.plot(cx, cy, "r^", markersize=12, zorder=10, label="배출원")

    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    _add_north_arrow(ax)
    _add_scalebar(ax, geom, (cx + x_range_down) - (cx - x_range_up))
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2, linestyle=":")

    fig.text(0.5, 0.01, f"사업명: {ctx.project_name}", ha="center", fontsize=9,
             color="gray")
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    return _fig_to_bytes(fig)


def _interpolate_air(data: list[tuple[float, float]], dist: float) -> float:
    """거리 기반으로 농도를 보간한다."""
    if not data:
        return 0.0
    sorted_data = sorted(data, key=lambda x: x[0])
    if dist <= sorted_data[0][0]:
        return sorted_data[0][1]
    if dist >= sorted_data[-1][0]:
        # 먼 거리에서는 급격히 감쇠
        last_d, last_v = sorted_data[-1]
        ratio = last_d / dist if dist > 0 else 1
        return last_v * ratio
    for i in range(len(sorted_data) - 1):
        d0, v0 = sorted_data[i]
        d1, v1 = sorted_data[i + 1]
        if d0 <= dist <= d1:
            ratio = (dist - d0) / (d1 - d0) if d1 != d0 else 0
            return v0 + (v1 - v0) * ratio
    return sorted_data[-1][1]


# ═══════════════════════════════════════════════════════════════
# 공통 유틸
# ═══════════════════════════════════════════════════════════════

def _fig_to_bytes(fig) -> bytes:
    """matplotlib Figure를 PNG bytes로 변환한다."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def render_map(map_type: str, ctx: MapRenderContext) -> bytes | None:
    """지정된 도면 유형을 렌더링한다.

    Args:
        map_type: location, land_use, monitoring_stations, noise_contour, air_dispersion
        ctx: 렌더링 컨텍스트

    Returns:
        PNG 바이트열 또는 None
    """
    renderers = {
        "location": render_location_map,
        "land_use": render_land_use_map,
        "monitoring_stations": render_monitoring_stations_map,
        "noise_contour": render_noise_contour_map,
        "air_dispersion": render_air_dispersion_map,
    }

    renderer = renderers.get(map_type)
    if renderer is None:
        return None

    try:
        return renderer(ctx)
    except Exception:
        # 예외 시에도 열린 figure를 반드시 정리하여 메모리 누수 방지
        plt.close("all")
        return None


def save_map(map_type: str, ctx: MapRenderContext) -> str | None:
    """도면을 PNG 파일로 저장하고 파일 경로를 반환한다."""
    data = render_map(map_type, ctx)
    if data is None:
        return None

    path = _get_output_path(ctx, map_type)
    path.write_bytes(data)
    return str(path)


def get_available_map_types() -> dict[str, str]:
    """사용 가능한 도면 유형 목록을 반환한다."""
    return dict(MAP_TYPES)
