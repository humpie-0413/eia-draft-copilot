"""GIS-1: 공간 분석 + 도면 렌더링 테스트.

spatial_analysis — 버퍼 분석, 중첩 탐색
map_renderer — 5종 도면 렌더링
"""

import math
import uuid
from unittest.mock import MagicMock, patch

import pytest
from shapely.geometry import Polygon, Point, mapping

from app.services.spatial_analysis import (
    BufferResult,
    OverlayItem,
    OverlayResult,
    compute_buffer,
    _haversine_distance,
)


# ═══════════════════════════════════════════════════════════════
# 공간 분석 테스트
# ═══════════════════════════════════════════════════════════════


class TestHaversineDistance:
    """Haversine 거리 계산 테스트."""

    def test_same_point(self):
        """동일 좌표는 거리 0."""
        d = _haversine_distance(37.5, 127.0, 37.5, 127.0)
        assert d == pytest.approx(0.0, abs=1.0)

    def test_known_distance(self):
        """서울~부산 직선거리 약 325km."""
        d = _haversine_distance(37.5665, 126.9780, 35.1796, 129.0756)
        assert 320_000 < d < 330_000  # 미터 단위

    def test_short_distance(self):
        """1km 미만 거리."""
        # 위도 0.01도 ≈ 약 1.1km
        d = _haversine_distance(37.500, 127.000, 37.510, 127.000)
        assert 1000 < d < 1200

    def test_symmetry(self):
        """거리 계산은 대칭적."""
        d1 = _haversine_distance(37.5, 127.0, 37.6, 127.1)
        d2 = _haversine_distance(37.6, 127.1, 37.5, 127.0)
        assert d1 == pytest.approx(d2, rel=1e-10)


class TestComputeBuffer:
    """버퍼 생성 테스트."""

    @pytest.fixture
    def mock_geometry_wkb(self):
        """강남구 사각형 폴리곤 WKB 목업."""
        poly = Polygon([
            (127.028, 37.498),
            (127.063, 37.498),
            (127.063, 37.517),
            (127.028, 37.517),
            (127.028, 37.498),
        ])
        # geoalchemy2 to_shape가 반환하는 형태를 모킹
        return poly

    def test_buffer_none_geometry(self):
        """geometry가 None이면 None 반환."""
        result = compute_buffer(None, 1000)
        assert result is None

    @patch("app.services.spatial_analysis.to_shape")
    def test_buffer_1km(self, mock_to_shape, mock_geometry_wkb):
        """1km 버퍼 생성."""
        mock_to_shape.return_value = mock_geometry_wkb
        result = compute_buffer("mock_wkb", 1000)

        assert result is not None
        assert result.radius_m == 1000
        assert result.buffer_geojson["type"] in ("Polygon", "MultiPolygon")
        assert result.area_km2 > 0
        assert len(result.centroid) == 2

    @patch("app.services.spatial_analysis.to_shape")
    def test_buffer_5km(self, mock_to_shape, mock_geometry_wkb):
        """5km 버퍼는 1km 버퍼보다 넓어야 한다."""
        mock_to_shape.return_value = mock_geometry_wkb

        buf_1k = compute_buffer("mock_wkb", 1000)
        buf_5k = compute_buffer("mock_wkb", 5000)

        assert buf_1k is not None
        assert buf_5k is not None
        assert buf_5k.area_km2 > buf_1k.area_km2

    @patch("app.services.spatial_analysis.to_shape")
    def test_buffer_centroid(self, mock_to_shape, mock_geometry_wkb):
        """버퍼 중심점이 원본 geometry 중심점과 같아야 한다."""
        mock_to_shape.return_value = mock_geometry_wkb
        result = compute_buffer("mock_wkb", 1000)

        assert result is not None
        lat, lon = result.centroid
        expected_lat = (37.498 + 37.517) / 2
        expected_lon = (127.028 + 127.063) / 2
        assert lat == pytest.approx(expected_lat, abs=0.001)
        assert lon == pytest.approx(expected_lon, abs=0.001)


class TestOverlayItem:
    """오버레이 항목 데이터 모델 테스트."""

    def test_creation(self):
        """OverlayItem 생성."""
        item = OverlayItem(
            name="강남 측정소",
            item_type="대기측정소",
            category="air_quality",
            distance_m=500.0,
            lat=37.505,
            lon=127.045,
        )
        assert item.name == "강남 측정소"
        assert item.distance_m == 500.0

    def test_default_metadata(self):
        """metadata 기본값은 빈 딕셔너리."""
        item = OverlayItem(
            name="test", item_type="test", category="test",
            distance_m=0, lat=0, lon=0,
        )
        assert item.metadata == {}


class TestOverlayResult:
    """오버레이 결과 데이터 모델 테스트."""

    def test_empty_result(self):
        """빈 오버레이 결과."""
        result = OverlayResult(
            project_id="test-id",
            radius_m=1000,
            items=[],
            total_count=0,
        )
        assert result.total_count == 0
        assert result.items == []

    def test_with_items(self):
        """항목이 포함된 오버레이 결과."""
        items = [
            OverlayItem(
                name=f"항목 {i}", item_type="대기측정소",
                category="air_quality", distance_m=i * 100,
                lat=37.5, lon=127.0,
            )
            for i in range(5)
        ]
        result = OverlayResult(
            project_id="test-id",
            radius_m=5000,
            items=items,
            total_count=5,
        )
        assert result.total_count == 5


# ═══════════════════════════════════════════════════════════════
# 도면 렌더링 테스트
# ═══════════════════════════════════════════════════════════════


class TestMapRenderer:
    """도면 렌더링 기본 테스트."""

    @pytest.fixture
    def mock_wkb(self):
        """모킹용 geometry WKB."""
        return "mock_wkb"

    @pytest.fixture
    def gangnam_polygon(self):
        """강남구 폴리곤."""
        return Polygon([
            (127.028, 37.498),
            (127.063, 37.498),
            (127.063, 37.517),
            (127.028, 37.517),
            (127.028, 37.498),
        ])

    def test_map_types_list(self):
        """도면 유형 목록."""
        from app.services.map_renderer import MAP_TYPES, get_available_map_types

        types = get_available_map_types()
        assert len(types) == 5
        assert "location" in types
        assert "land_use" in types
        assert "monitoring_stations" in types
        assert "noise_contour" in types
        assert "air_dispersion" in types

    @patch("app.services.map_renderer.to_shape")
    def test_render_location_map(self, mock_to_shape, gangnam_polygon):
        """위치도 렌더링."""
        mock_to_shape.return_value = gangnam_polygon

        from app.services.map_renderer import MapRenderContext, render_location_map

        ctx = MapRenderContext(
            project_id="test-id",
            project_name="테스트 사업",
            geometry_wkb="mock_wkb",
            overlay_items=[
                OverlayItem(
                    name="강남 측정소", item_type="대기측정소",
                    category="air_quality", distance_m=500,
                    lat=37.505, lon=127.045,
                ),
            ],
        )

        result = render_location_map(ctx)
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 1000  # PNG는 최소 수백 바이트
        # PNG 시그니처 확인
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    @patch("app.services.map_renderer.to_shape")
    def test_render_land_use_map(self, mock_to_shape, gangnam_polygon):
        """토지이용현황도 렌더링."""
        mock_to_shape.return_value = gangnam_polygon

        from app.services.map_renderer import MapRenderContext, render_land_use_map

        ctx = MapRenderContext(
            project_id="test-id",
            project_name="테스트 사업",
            geometry_wkb="mock_wkb",
            land_use_data=[
                {"zone_name": "주거지역", "indicator": "용도지역"},
                {"zone_name": "녹지지역", "indicator": "용도지역"},
            ],
        )

        result = render_land_use_map(ctx)
        assert result is not None
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    @patch("app.services.map_renderer.to_shape")
    def test_render_monitoring_stations_map(self, mock_to_shape, gangnam_polygon):
        """환경측정소 분포도 렌더링."""
        mock_to_shape.return_value = gangnam_polygon

        from app.services.map_renderer import MapRenderContext, render_monitoring_stations_map

        ctx = MapRenderContext(
            project_id="test-id",
            project_name="테스트 사업",
            geometry_wkb="mock_wkb",
            overlay_items=[
                OverlayItem(
                    name="강남 대기", item_type="대기측정소",
                    category="air_quality", distance_m=300,
                    lat=37.505, lon=127.045,
                ),
                OverlayItem(
                    name="한강 수질", item_type="수질측정소",
                    category="water_quality", distance_m=800,
                    lat=37.510, lon=127.050,
                ),
            ],
        )

        result = render_monitoring_stations_map(ctx)
        assert result is not None
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    @patch("app.services.map_renderer.to_shape")
    def test_render_noise_contour_map(self, mock_to_shape, gangnam_polygon):
        """소음 등고선도 렌더링."""
        mock_to_shape.return_value = gangnam_polygon

        from app.services.map_renderer import MapRenderContext, render_noise_contour_map
        from app.services.prediction.base import PredictionItem, PredictionResult

        # 소음 예측 결과 모킹
        predictions = [
            PredictionItem(
                label=f"{d}m", distance_m=float(d),
                pollutant="소음_Leq_주간",
                predicted_concentration=90 - 20 * math.log10(max(d, 1)),
                background_concentration=50.0,
                total_concentration=max(90 - 20 * math.log10(max(d, 1)), 50),
                unit="dB(A)", standard_value=55.0,
                exceeds_standard=(90 - 20 * math.log10(max(d, 1))) > 55,
            )
            for d in [10, 20, 50, 100, 200, 500]
        ]

        pr = PredictionResult(
            section_key="noise_vibration",
            model_name="noise_propagation",
            input_parameters={},
            predictions=predictions,
        )

        ctx = MapRenderContext(
            project_id="test-id",
            project_name="테스트 사업",
            geometry_wkb="mock_wkb",
            prediction_result=pr,
        )

        result = render_noise_contour_map(ctx)
        assert result is not None
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    @patch("app.services.map_renderer.to_shape")
    def test_render_air_dispersion_map(self, mock_to_shape, gangnam_polygon):
        """대기확산 예측도 렌더링."""
        mock_to_shape.return_value = gangnam_polygon

        from app.services.map_renderer import MapRenderContext, render_air_dispersion_map
        from app.services.prediction.base import PredictionItem, PredictionResult

        predictions = [
            PredictionItem(
                label=f"{d}m", distance_m=float(d),
                pollutant="PM10",
                predicted_concentration=100 / max(d / 100, 0.1),
                background_concentration=45.0,
                total_concentration=45.0 + 100 / max(d / 100, 0.1),
                unit="ug/m3", standard_value=50.0,
                exceeds_standard=(45.0 + 100 / max(d / 100, 0.1)) > 50,
            )
            for d in [100, 200, 500, 1000, 2000, 5000]
        ]

        pr = PredictionResult(
            section_key="air_quality",
            model_name="gaussian_plume",
            input_parameters={},
            predictions=predictions,
        )

        ctx = MapRenderContext(
            project_id="test-id",
            project_name="테스트 사업",
            geometry_wkb="mock_wkb",
            prediction_result=pr,
        )

        result = render_air_dispersion_map(ctx)
        assert result is not None
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_render_without_geometry(self):
        """geometry 없으면 None 반환."""
        from app.services.map_renderer import MapRenderContext, render_map

        ctx = MapRenderContext(
            project_id="test-id",
            project_name="테스트 사업",
            geometry_wkb=None,
        )

        for map_type in ["location", "land_use", "monitoring_stations",
                          "noise_contour", "air_dispersion"]:
            result = render_map(map_type, ctx)
            assert result is None

    def test_render_unknown_type(self):
        """알 수 없는 도면 유형이면 None 반환."""
        from app.services.map_renderer import MapRenderContext, render_map

        ctx = MapRenderContext(
            project_id="test-id",
            project_name="테스트 사업",
        )
        result = render_map("unknown_type", ctx)
        assert result is None


class TestNoiseInterpolation:
    """소음 보간 함수 테스트."""

    def test_empty_data(self):
        """빈 데이터."""
        from app.services.map_renderer import _interpolate_noise
        assert _interpolate_noise([], 100) == 0.0

    def test_before_first(self):
        """첫 번째 데이터 포인트 이전."""
        from app.services.map_renderer import _interpolate_noise
        data = [(100, 70.0), (200, 60.0), (500, 50.0)]
        assert _interpolate_noise(data, 50) == 70.0

    def test_after_last(self):
        """마지막 데이터 포인트 이후."""
        from app.services.map_renderer import _interpolate_noise
        data = [(100, 70.0), (200, 60.0), (500, 50.0)]
        assert _interpolate_noise(data, 1000) == 50.0

    def test_interpolation(self):
        """중간 보간."""
        from app.services.map_renderer import _interpolate_noise
        data = [(100, 70.0), (200, 60.0)]
        result = _interpolate_noise(data, 150)
        assert result == pytest.approx(65.0, abs=0.1)

    def test_exact_point(self):
        """정확한 데이터 포인트."""
        from app.services.map_renderer import _interpolate_noise
        data = [(100, 70.0), (200, 60.0), (500, 50.0)]
        assert _interpolate_noise(data, 100) == pytest.approx(70.0)


class TestAirInterpolation:
    """대기 보간 함수 테스트."""

    def test_empty_data(self):
        """빈 데이터."""
        from app.services.map_renderer import _interpolate_air
        assert _interpolate_air([], 100) == 0.0

    def test_decay_beyond_range(self):
        """범위 이후 감쇠."""
        from app.services.map_renderer import _interpolate_air
        data = [(100, 100.0), (500, 60.0), (1000, 50.0)]
        result = _interpolate_air(data, 2000)
        assert result < 50.0  # 감쇠해야 함
        assert result > 0  # 0보다는 커야 함


class TestBufferResult:
    """BufferResult 데이터 모델 테스트."""

    def test_creation(self):
        """BufferResult 생성."""
        result = BufferResult(
            project_id="test",
            radius_m=1000,
            buffer_geojson={"type": "Polygon", "coordinates": []},
            centroid=(37.5, 127.0),
            area_km2=3.14,
        )
        assert result.radius_m == 1000
        assert result.area_km2 == 3.14
