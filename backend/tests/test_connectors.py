"""커넥터 연동 테스트.

실제 외부 API를 호출하지 않고 httpx 응답을 모킹하여
fetch → normalize → collect 파이프라인을 검증한다.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import Request, Response

from app.config import settings
from app.connectors.keco_air import KecoAirConnector
from app.connectors.kma_weather import KmaWeatherConnector
from app.connectors.soil_info import SoilInfoConnector
from app.connectors.traffic_volume import TrafficVolumeConnector
from app.connectors.waste_stats import WasteStatsConnector
from app.connectors.water_info import WaterInfoConnector
from app.connectors.registry import get_connector, connector_registry
from app.schemas.evidence import EvidenceCategory


# ──────────────────────────────────────────────────
# 에어코리아 대기질 커넥터 테스트
# ──────────────────────────────────────────────────


class TestKecoAirConnector:
    """에어코리아 대기질 커넥터 단위 테스트."""

    def setup_method(self):
        self.connector = KecoAirConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    # 샘플 API 응답
    SAMPLE_RESPONSE = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
            "body": {
                "totalCount": 2,
                "items": [
                    {
                        "dataTime": "2026-03-12 14:00",
                        "stationName": "종로구",
                        "pm10Value": "45",
                        "pm25Value": "22",
                        "o3Value": "0.035",
                        "no2Value": "0.028",
                        "so2Value": "0.004",
                        "coValue": "0.5",
                        "pm10Grade": "2",
                        "pm25Grade": "2",
                    },
                    {
                        "dataTime": "2026-03-12 13:00",
                        "stationName": "종로구",
                        "pm10Value": "42",
                        "pm25Value": "-",
                        "o3Value": "0.030",
                        "no2Value": None,
                        "so2Value": "0.003",
                        "coValue": "0.4",
                    },
                ],
            },
        }
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 첫 번째 항목: 6개 지표 전부 유효
        # 두 번째 항목: pm25="-" 건너뜀, no2=None 건너뜀 → 4개
        assert len(evidences) == 10

    def test_normalize_지표_값_검증(self):
        """지표 값과 단위가 올바르게 매핑되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        pm10 = next(e for e in evidences if e.indicator == "PM10")
        assert pm10.value == "45"
        assert pm10.numeric_value == 45.0
        assert pm10.unit == "ug/m3"
        assert pm10.category == EvidenceCategory.AIR_QUALITY

    def test_normalize_측정시각_파싱(self):
        """측정 시각이 datetime으로 올바르게 파싱되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.observed_at == datetime(2026, 3, 12, 14, 0)

    def test_normalize_메타데이터_포함(self):
        """메타데이터에 측정소명과 시각이 포함되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.metadata_json["station_name"] == "종로구"
        assert first.metadata_json["data_time"] == "2026-03-12 14:00"

    def test_normalize_대시_값_건너뛰기(self):
        """'-' 값이 올바르게 건너뛰어지는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 두 번째 항목의 PM2.5는 "-"이므로 건너뜀
        second_pm25 = [
            e
            for e in evidences
            if e.indicator == "PM2.5"
            and e.metadata_json.get("data_time") == "2026-03-12 13:00"
        ]
        assert len(second_pm25) == 0

    def test_normalize_빈_응답(self):
        """items가 비어있을 때 빈 리스트를 반환하는지 확인."""
        empty_payload = {
            "response": {"body": {"items": [], "totalCount": 0}}
        }
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert evidences == []

    def test_normalize_screening_only_태깅(self):
        """screening_only 플래그가 올바르게 전달되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
            screening_only=True,
        )
        assert all(e.screening_only for e in evidences)

    @pytest.mark.asyncio
    async def test_fetch_API키_미설정(self):
        """API 키가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.keco_air.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = ""
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="DATA_GO_KR_API_KEY"):
                await self.connector.fetch({"station_name": "종로구"})

    @pytest.mark.asyncio
    async def test_fetch_측정소명_누락(self):
        """station_name이 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.keco_air.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="station_name"):
                await self.connector.fetch({})

    @pytest.mark.asyncio
    async def test_fetch_정상_호출(self):
        """외부 API가 정상 응답을 반환할 때 데이터가 올바르게 반환되는지 확인."""
        mock_response = Response(
            status_code=200,
            json=self.SAMPLE_RESPONSE,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.keco_air.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await self.connector.fetch(
                    {"station_name": "종로구", "data_term": "DAILY"}
                )

                assert result == self.SAMPLE_RESPONSE
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_API_오류_응답(self):
        """API가 오류 코드를 반환할 때 RuntimeError가 발생하는지 확인."""
        error_response = {
            "response": {
                "header": {
                    "resultCode": "99",
                    "resultMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
                },
                "body": {},
            }
        }
        mock_response = Response(
            status_code=200,
            json=error_response,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.keco_air.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "invalid_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                with pytest.raises(RuntimeError, match="에어코리아 API 오류"):
                    await self.connector.fetch({"station_name": "종로구"})


# ──────────────────────────────────────────────────
# 국립환경과학원 수질 DB 커넥터 테스트
# ──────────────────────────────────────────────────


class TestWaterInfoConnector:
    """국립환경과학원 수질 DB (물환경 수질측정망) 커넥터 단위 테스트."""

    def setup_method(self):
        self.connector = WaterInfoConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    # 샘플 API 응답 — 국립환경과학원 수질 DB 실제 구조
    SAMPLE_RESPONSE = {
        "getWaterMeasuringList": {
            "header": {"code": "00", "message": "NORMAL SERVICE"},
            "item": [
                {
                    "PT_NO": "3008A70",
                    "PT_NM": "팔당댐",
                    "WMCYMD": "2024.03.01",
                    "WMYR": "2024",
                    "WMOD": "03",
                    "ITEM_BOD": "         1.2",
                    "ITEM_COD": "         3.5",
                    "ITEM_SS": "         8.0",
                    "ITEM_DOC": "         9.5",
                    "ITEM_TN": "         2.100",
                    "ITEM_TP": "         0.030",
                },
                {
                    "PT_NO": "3008A70",
                    "PT_NM": "팔당댐",
                    "WMCYMD": "2024.02.15",
                    "WMYR": "2024",
                    "WMOD": "02",
                    "ITEM_BOD": "         1.0",
                    "ITEM_COD": "",
                    "ITEM_SS": "         6.5",
                    "ITEM_DOC": "        10.2",
                    "ITEM_TN": None,
                    "ITEM_TP": "         0.020",
                },
            ],
            "numOfRows": 100,
            "pageNo": 1,
            "totalCount": 2,
        }
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 첫 번째: 6개 전부 유효
        # 두 번째: ITEM_COD="" 건너뜀, ITEM_TN=None 건너뜀 → 4개
        assert len(evidences) == 10

    def test_normalize_지표_값_검증(self):
        """지표 값과 단위가 올바르게 매핑되는지 확인 (공백 제거 포함)."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        bod = next(e for e in evidences if e.indicator == "BOD")
        assert bod.value == "1.2"
        assert bod.numeric_value == 1.2
        assert bod.unit == "mg/L"
        assert bod.category == EvidenceCategory.WATER_QUALITY

    def test_normalize_측정일_파싱(self):
        """YYYY.MM.DD 형식의 측정일이 올바르게 파싱되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.observed_at == datetime(2024, 3, 1)

    def test_normalize_메타데이터_포함(self):
        """메타데이터에 측정지점 정보가 포함되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.metadata_json["site_name"] == "팔당댐"
        assert first.metadata_json["site_id"] == "3008A70"

    def test_normalize_빈_값_건너뛰기(self):
        """빈 문자열과 None 값이 올바르게 건너뛰어지는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 두 번째 항목의 COD는 ""이므로 건너뜀
        second_cod = [
            e
            for e in evidences
            if e.indicator == "COD"
            and e.metadata_json.get("measure_date") == "2024.02.15"
        ]
        assert len(second_cod) == 0

    def test_normalize_빈_응답(self):
        """item이 비어있을 때 빈 리스트를 반환하는지 확인."""
        empty_payload = {
            "getWaterMeasuringList": {
                "header": {"code": "00", "message": "NORMAL SERVICE"},
                "item": [],
                "totalCount": 0,
            }
        }
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert evidences == []

    @pytest.mark.asyncio
    async def test_fetch_API키_미설정(self):
        """API 키가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.water_info.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = ""
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="DATA_GO_KR_API_KEY"):
                await self.connector.fetch({"year": "2024"})

    @pytest.mark.asyncio
    async def test_fetch_필수_파라미터_누락(self):
        """year가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.water_info.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="year"):
                await self.connector.fetch({})

    @pytest.mark.asyncio
    async def test_fetch_정상_호출(self):
        """외부 API가 정상 응답을 반환할 때 데이터가 올바르게 반환되는지 확인."""
        mock_response = Response(
            status_code=200,
            json=self.SAMPLE_RESPONSE,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.water_info.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await self.connector.fetch(
                    {"year": "2024", "pt_no": "3008A70"}
                )

                assert result == self.SAMPLE_RESPONSE
                mock_client.get.assert_called_once()


# ──────────────────────────────────────────────────
# 토양측정망 커넥터 테스트
# ──────────────────────────────────────────────────


class TestSoilInfoConnector:
    """국립환경과학원 토양측정망 커넥터 단위 테스트."""

    def setup_method(self):
        self.connector = SoilInfoConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    # 샘플 API 응답 — 국립환경과학원 토양측정망 구조
    SAMPLE_RESPONSE = {
        "getSoilMeasuringList": {
            "header": {"code": "00", "message": "NORMAL SERVICE"},
            "item": [
                {
                    "PT_NO": "S001",
                    "PT_NM": "서울 강남",
                    "MEASURE_DT": "2024.06.15",
                    "ITEM_CD": "         0.12",
                    "ITEM_CU": "         8.5",
                    "ITEM_PB": "        12.3",
                    "ITEM_ZN": "        45.0",
                    "ITEM_NI": "         3.2",
                    "ITEM_CR6": "         0.05",
                    "ITEM_PH": "         6.8",
                    "ITEM_OM": "         3.5",
                },
                {
                    "PT_NO": "S002",
                    "PT_NM": "부산 해운대",
                    "MEASURE_DT": "2024.06.20",
                    "ITEM_CD": "         0.08",
                    "ITEM_CU": "",
                    "ITEM_PB": "         9.1",
                    "ITEM_ZN": None,
                    "ITEM_NI": "         2.1",
                    "ITEM_CR6": "         0.03",
                    "ITEM_PH": "         7.1",
                    "ITEM_OM": "         2.8",
                },
            ],
            "numOfRows": 100,
            "pageNo": 1,
            "totalCount": 2,
        }
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 첫 번째: 8개 지표 전부 유효
        # 두 번째: ITEM_CU="" 건너뜀, ITEM_ZN=None 건너뜀 → 6개
        assert len(evidences) == 14

    def test_normalize_지표_값_검증(self):
        """지표 값과 단위가 올바르게 매핑되는지 확인 (공백 제거 포함)."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        cd = next(e for e in evidences if e.indicator == "Cd")
        assert cd.value == "0.12"
        assert cd.numeric_value == 0.12
        assert cd.unit == "mg/kg"
        assert cd.category == EvidenceCategory.SOIL

    def test_normalize_pH_지표(self):
        """pH 지표가 단위 없이 올바르게 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        ph = next(e for e in evidences if e.indicator == "pH")
        assert ph.value == "6.8"
        assert ph.numeric_value == 6.8
        assert ph.unit == ""

    def test_normalize_측정일_파싱(self):
        """YYYY.MM.DD 형식의 측정일이 올바르게 파싱되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.observed_at == datetime(2024, 6, 15)

    def test_normalize_메타데이터_포함(self):
        """메타데이터에 측정지점 정보가 포함되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.metadata_json["site_name"] == "서울 강남"
        assert first.metadata_json["site_code"] == "S001"

    def test_normalize_빈_값_건너뛰기(self):
        """빈 문자열과 None 값이 올바르게 건너뛰어지는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 두 번째 항목의 Cu는 ""이므로 건너뜀
        second_cu = [
            e
            for e in evidences
            if e.indicator == "Cu"
            and e.metadata_json.get("site_code") == "S002"
        ]
        assert len(second_cu) == 0

    def test_normalize_빈_응답(self):
        """item이 비어있을 때 빈 리스트를 반환하는지 확인."""
        empty_payload = {
            "getSoilMeasuringList": {
                "header": {"code": "00", "message": "NORMAL SERVICE"},
                "item": [],
                "totalCount": 0,
            }
        }
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert evidences == []

    def test_normalize_screening_only_태깅(self):
        """screening_only 플래그가 올바르게 전달되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
            screening_only=True,
        )
        assert all(e.screening_only for e in evidences)

    @pytest.mark.asyncio
    async def test_fetch_API키_미설정(self):
        """API 키가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.soil_info.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = ""
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="DATA_GO_KR_API_KEY"):
                await self.connector.fetch({"year": "2024"})

    @pytest.mark.asyncio
    async def test_fetch_필수_파라미터_누락(self):
        """year가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.soil_info.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="year"):
                await self.connector.fetch({})

    @pytest.mark.asyncio
    async def test_fetch_정상_호출(self):
        """외부 API가 정상 응답을 반환할 때 데이터가 올바르게 반환되는지 확인."""
        mock_response = Response(
            status_code=200,
            json=self.SAMPLE_RESPONSE,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.soil_info.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await self.connector.fetch(
                    {"year": "2024", "site_code": "S001"}
                )

                assert result == self.SAMPLE_RESPONSE
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_API_오류_응답(self):
        """API가 오류 코드를 반환할 때 RuntimeError가 발생하는지 확인."""
        error_response = {
            "getSoilMeasuringList": {
                "header": {
                    "code": "99",
                    "message": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
                },
            }
        }
        mock_response = Response(
            status_code=200,
            json=error_response,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.soil_info.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "invalid_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                with pytest.raises(RuntimeError, match="토양측정망 API 오류"):
                    await self.connector.fetch({"year": "2024"})


# ──────────────────────────────────────────────────
# 기상청 ASOS 커넥터 테스트
# ──────────────────────────────────────────────────


class TestKmaWeatherConnector:
    """기상청 종관기상관측(ASOS) 커넥터 단위 테스트."""

    def setup_method(self):
        self.connector = KmaWeatherConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    # 샘플 API 응답 — 기상청 ASOS 일자료 구조
    SAMPLE_RESPONSE = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
            "body": {
                "dataType": "JSON",
                "items": {
                    "item": [
                        {
                            "stnId": "108",
                            "stnNm": "서울",
                            "tm": "2024-01-15",
                            "avgTa": "1.5",
                            "maxTa": "5.2",
                            "minTa": "-2.1",
                            "sumRn": "0.0",
                            "avgWs": "2.3",
                            "maxWs": "5.1",
                            "avgRhm": "55.2",
                        },
                        {
                            "stnId": "108",
                            "stnNm": "서울",
                            "tm": "2024-01-16",
                            "avgTa": "3.0",
                            "maxTa": "7.8",
                            "minTa": "",
                            "sumRn": "12.5",
                            "avgWs": None,
                            "maxWs": "8.3",
                            "avgRhm": "72.0",
                        },
                    ]
                },
                "numOfRows": 999,
                "pageNo": 1,
                "totalCount": 2,
            },
        }
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 첫 번째: 7개 지표 전부 유효
        # 두 번째: minTa="" 건너뜀, avgWs=None 건너뜀 → 5개
        assert len(evidences) == 12

    def test_normalize_지표_값_검증(self):
        """지표 값과 단위가 올바르게 매핑되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        avg_ta = next(e for e in evidences if e.indicator == "평균기온")
        assert avg_ta.value == "1.5"
        assert avg_ta.numeric_value == 1.5
        assert avg_ta.unit == "\u2103"
        assert avg_ta.category == EvidenceCategory.CLIMATE

    def test_normalize_강수량_검증(self):
        """강수량 0.0이 유효한 값으로 처리되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        rain = next(
            e
            for e in evidences
            if e.indicator == "강수량"
            and e.metadata_json.get("date") == "2024-01-15"
        )
        assert rain.value == "0.0"
        assert rain.numeric_value == 0.0
        assert rain.unit == "mm"

    def test_normalize_관측일_파싱(self):
        """YYYY-MM-DD 형식의 관측일이 올바르게 파싱되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.observed_at == datetime(2024, 1, 15)

    def test_normalize_메타데이터_포함(self):
        """메타데이터에 관측소 정보가 포함되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        first = evidences[0]
        assert first.metadata_json["station_name"] == "서울"
        assert first.metadata_json["station_id"] == "108"

    def test_normalize_빈_값_건너뛰기(self):
        """빈 문자열과 None 값이 올바르게 건너뛰어지는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )

        # 두 번째 항목의 최저기온은 ""이므로 건너뜀
        second_min = [
            e
            for e in evidences
            if e.indicator == "최저기온"
            and e.metadata_json.get("date") == "2024-01-16"
        ]
        assert len(second_min) == 0

    def test_normalize_빈_응답(self):
        """items가 비어있을 때 빈 리스트를 반환하는지 확인."""
        empty_payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                "body": {
                    "items": {"item": []},
                    "totalCount": 0,
                },
            }
        }
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert evidences == []

    def test_normalize_screening_only_태깅(self):
        """screening_only 플래그가 올바르게 전달되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
            screening_only=True,
        )
        assert all(e.screening_only for e in evidences)

    @pytest.mark.asyncio
    async def test_fetch_API키_미설정(self):
        """API 키가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.kma_weather.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = ""
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="DATA_GO_KR_API_KEY"):
                await self.connector.fetch({
                    "stn_id": "108",
                    "start_dt": "20240101",
                    "end_dt": "20240131",
                })

    @pytest.mark.asyncio
    async def test_fetch_필수_파라미터_누락_관측소(self):
        """stn_id가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.kma_weather.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="stn_id"):
                await self.connector.fetch({
                    "start_dt": "20240101",
                    "end_dt": "20240131",
                })

    @pytest.mark.asyncio
    async def test_fetch_필수_파라미터_누락_기간(self):
        """start_dt/end_dt가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.kma_weather.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="start_dt"):
                await self.connector.fetch({"stn_id": "108"})

    @pytest.mark.asyncio
    async def test_fetch_정상_호출(self):
        """외부 API가 정상 응답을 반환할 때 데이터가 올바르게 반환되는지 확인."""
        mock_response = Response(
            status_code=200,
            json=self.SAMPLE_RESPONSE,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.kma_weather.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await self.connector.fetch({
                    "stn_id": "108",
                    "start_dt": "20240101",
                    "end_dt": "20240131",
                })

                assert result == self.SAMPLE_RESPONSE
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_API_오류_응답(self):
        """API가 오류 코드를 반환할 때 RuntimeError가 발생하는지 확인."""
        error_response = {
            "response": {
                "header": {
                    "resultCode": "99",
                    "resultMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
                },
                "body": {},
            }
        }
        mock_response = Response(
            status_code=200,
            json=error_response,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.kma_weather.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "invalid_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                with pytest.raises(RuntimeError, match="기상청 ASOS API 오류"):
                    await self.connector.fetch({
                        "stn_id": "108",
                        "start_dt": "20240101",
                        "end_dt": "20240131",
                    })


# ──────────────────────────────────────────────────
# V-world 토지이용계획 커넥터 테스트
# ──────────────────────────────────────────────────


class TestLandUseConnector:
    """V-world 토지이용계획 커넥터 단위 테스트."""

    def setup_method(self):
        from app.connectors.land_use import LandUseConnector
        self.connector = LandUseConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    SAMPLE_RESPONSE = {
        "response": {
            "status": "OK",
            "record": {"total": "2"},
            "result": {
                "featureCollection": {
                    "features": [
                        {
                            "properties": {
                                "PRPOS_AREA_NM": "제1종일반주거지역",
                                "JIMOK": "대",
                            }
                        },
                        {
                            "properties": {
                                "PRPOS_AREA_NM": "자연녹지지역",
                                "JIMOK": "전",
                            }
                        },
                    ]
                }
            },
        }
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        # 용도지역구분 1건 + 지목 1건 + 용도지구 1건 = 3건
        assert len(evidences) == 3

    def test_normalize_용도지역(self):
        """용도지역구분 지표가 올바르게 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        zone = next(e for e in evidences if e.indicator == "용도지역구분")
        assert "제1종일반주거지역" in zone.value
        assert "자연녹지지역" in zone.value
        assert zone.category == EvidenceCategory.LAND_USE

    def test_normalize_지목(self):
        """지목 지표가 올바르게 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        jimok = next(e for e in evidences if e.indicator == "지목")
        assert "대" in jimok.value
        assert "전" in jimok.value

    def test_normalize_빈_응답(self):
        """빈 응답 시 빈 리스트를 반환하는지 확인."""
        empty_payload = {
            "response": {
                "status": "OK",
                "record": {"total": "0"},
                "result": {"featureCollection": {"features": []}},
            }
        }
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert len(evidences) == 0

    def test_커넥터_메타데이터(self):
        """커넥터 키와 표시명이 올바른지 확인."""
        assert self.connector.connector_key == "vworld_land_use"
        assert "토지이용" in self.connector.display_name

    @pytest.mark.asyncio
    async def test_fetch_키_미설정(self):
        """VWORLD_API_KEY 미설정 시 ValueError를 발생시키는지 확인."""
        with patch.object(settings, "VWORLD_API_KEY", ""):
            with pytest.raises(ValueError, match="VWORLD_API_KEY"):
                await self.connector.fetch({"lng": 127.0, "lat": 37.5})

    @pytest.mark.asyncio
    async def test_fetch_파라미터_누락(self):
        """필수 파라미터 누락 시 ValueError를 발생시키는지 확인."""
        with patch.object(settings, "VWORLD_API_KEY", "test_key"):
            with pytest.raises(ValueError, match="lng"):
                await self.connector.fetch({})


# ──────────────────────────────────────────────────
# 국가유산청 문화재 커넥터 테스트
# ──────────────────────────────────────────────────


class TestCulturalHeritageConnector:
    """국가유산청 문화재 커넥터 단위 테스트."""

    def setup_method(self):
        from app.connectors.cultural_heritage import CulturalHeritageConnector
        self.connector = CulturalHeritageConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    SAMPLE_RESPONSE = {
        "total_count": 50,
        "filtered_count": 2,
        "center_lat": 37.5075,
        "center_lng": 127.0455,
        "sido_code": "11",
        "radius_m": 1000,
        "items": [
            {
                "ccbaMnm1": "봉은사",
                "ccbaKdcd": "13",
                "ccbaLcad": "서울특별시 강남구 봉은사로 531",
                "ccbaAsno": "001234",
                "ccbaCtcdNm": "서울특별시",
                "distance_m": 450,
                "latitude": "37.5145",
                "longitude": "127.0575",
            },
            {
                "ccbaMnm1": "삼성동 고분",
                "ccbaKdcd": "13",
                "ccbaLcad": "서울특별시 강남구 삼성동",
                "ccbaAsno": "005678",
                "ccbaCtcdNm": "서울특별시",
                "distance_m": 820,
                "latitude": "37.5100",
                "longitude": "127.0500",
            },
        ],
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        # 문화재 2건 x (문화재명 + 종별 + 이격거리 + 소재지) = 8건
        assert len(evidences) == 8

    def test_normalize_문화재명(self):
        """문화재명 지표가 올바르게 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        names = [e for e in evidences if e.indicator == "문화재명"]
        assert len(names) == 2
        assert names[0].value == "봉은사"
        assert names[0].category == EvidenceCategory.CULTURAL_HERITAGE

    def test_normalize_이격거리(self):
        """이격거리 지표가 수치값과 함께 올바르게 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        distances = [e for e in evidences if e.indicator == "이격거리"]
        assert len(distances) == 2
        assert distances[0].numeric_value == 450.0
        assert distances[0].unit == "m"

    def test_normalize_종별(self):
        """종별 코드가 한글명으로 변환되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        kinds = [e for e in evidences if e.indicator == "종별"]
        assert len(kinds) == 2
        assert kinds[0].value == "사적"

    def test_normalize_빈_응답(self):
        """빈 응답 시 빈 리스트를 반환하는지 확인."""
        empty_payload = {
            "total_count": 0, "filtered_count": 0,
            "center_lat": 37.5, "center_lng": 127.0,
            "sido_code": "11", "radius_m": 1000,
            "items": [],
        }
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert len(evidences) == 0

    def test_커넥터_메타데이터(self):
        """커넥터 키와 표시명이 올바른지 확인."""
        assert self.connector.connector_key == "cultural_heritage"
        assert "문화재" in self.connector.display_name

    def test_haversine_거리계산(self):
        """Haversine 거리 계산이 올바른지 확인."""
        from app.connectors.cultural_heritage import _haversine_distance
        # 서울역 (37.5547, 126.9707) → 강남역 (37.4979, 127.0276)
        dist = _haversine_distance(37.5547, 126.9707, 37.4979, 127.0276)
        assert 7000 < dist < 9000  # 약 7.5~8km

    def test_좌표_시도코드_변환(self):
        """좌표에서 시도코드가 올바르게 추론되는지 확인."""
        from app.connectors.cultural_heritage import _coord_to_sido
        assert _coord_to_sido(37.5, 127.0) == "11"  # 서울
        assert _coord_to_sido(35.1, 129.0) == "21"  # 부산

    @pytest.mark.asyncio
    async def test_fetch_파라미터_누락(self):
        """필수 파라미터 누락 시 ValueError를 발생시키는지 확인."""
        with pytest.raises(ValueError, match="lat"):
            await self.connector.fetch({})

    def test_종류코드_변환(self):
        """문화재 종류 코드가 올바르게 한글명으로 변환되는지 확인."""
        from app.connectors.cultural_heritage import CulturalHeritageConnector
        assert CulturalHeritageConnector._kind_code_to_name("11") == "국보"
        assert CulturalHeritageConnector._kind_code_to_name("12") == "보물"
        assert CulturalHeritageConnector._kind_code_to_name("13") == "사적"
        assert CulturalHeritageConnector._kind_code_to_name("99") == "99"


# ──────────────────────────────────────────────────
# 한국건설기술연구원 교통량 통계 커넥터 테스트
# ──────────────────────────────────────────────────


class TestTrafficVolumeConnector:
    """한국건설기술연구원 교통량 통계 커넥터 단위 테스트."""

    def setup_method(self):
        self.connector = TrafficVolumeConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    # 교통량 통계 샘플 응답 — traffic 배열 형태
    SAMPLE_RESPONSE = {
        "resultCode": "0",
        "resultMsg": "OK",
        "year": 2023,
        "dtype": 2,
        "count": 3,
        "traffic": [
            {
                "spot_id": "A001",
                "spot_nm": "서울-수원 구간",
                "aadt": "25000",
                "road_grade": "일반국도",
            },
            {
                "spot_id": "A002",
                "spot_nm": "수원-평택 구간",
                "aadt": "18500",
                "road_grade": "일반국도",
            },
            {
                "spot_id": "A003",
                "spot_nm": "평택-천안 구간",
                "aadt": None,
                "road_grade": "일반국도",
            },
        ],
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        # 첫 번째: 교통량_현황 + 도로등급 + 도로명 = 3
        # 두 번째: 교통량_현황 + 도로등급 + 도로명 = 3
        # 세 번째: aadt=None → 건너뜀, 도로등급 + 도로명 = 2
        assert len(evidences) == 8

    def test_normalize_교통량_값_검증(self):
        """교통량 지표 값과 단위가 올바르게 매핑되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        traffic = next(e for e in evidences if e.indicator == "교통량_현황")
        assert traffic.value == "25000"
        assert traffic.numeric_value == 25000.0
        assert traffic.unit == "대/일"
        assert traffic.category == EvidenceCategory.TRAFFIC

    def test_normalize_도로명_추출(self):
        """도로명 지표가 올바르게 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        road_names = [e for e in evidences if e.indicator == "도로명"]
        assert len(road_names) == 3
        assert road_names[0].value == "서울-수원 구간"

    def test_normalize_도로등급_추출(self):
        """도로등급 지표가 올바르게 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        grades = [e for e in evidences if e.indicator == "도로등급"]
        assert len(grades) == 3
        assert grades[0].value == "일반국도"

    def test_normalize_메타데이터_포함(self):
        """메타데이터에 지점명과 도로유형이 포함되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        traffic = next(e for e in evidences if e.indicator == "교통량_현황")
        assert traffic.metadata_json["spot_name"] == "서울-수원 구간"
        assert traffic.metadata_json["road_type"] == "일반국도"

    def test_normalize_빈_응답(self):
        """데이터가 없을 때 빈 리스트를 반환하는지 확인."""
        empty_payload = {"resultCode": "0", "traffic": []}
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert evidences == []

    def test_normalize_screening_only_태깅(self):
        """screening_only 플래그가 올바르게 전달되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
            screening_only=True,
        )
        assert all(e.screening_only for e in evidences)

    def test_normalize_응답구조_패턴2(self):
        """response.body.items 패턴도 처리하는지 확인."""
        alt_payload = {
            "response": {
                "body": {
                    "items": [
                        {"spotNm": "구간1", "AADT": "12000"},
                    ]
                }
            }
        }
        evidences = self.connector.normalize(
            raw_payload=alt_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        traffic = [e for e in evidences if e.indicator == "교통량_현황"]
        assert len(traffic) == 1
        assert traffic[0].numeric_value == 12000.0

    def test_normalize_쉼표_교통량(self):
        """쉼표가 포함된 교통량 값을 올바르게 파싱하는지 확인."""
        payload = {
            "traffic": [
                {"spot_nm": "구간A", "aadt": "1,250,000"},
            ]
        }
        evidences = self.connector.normalize(
            raw_payload=payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        traffic = next(e for e in evidences if e.indicator == "교통량_현황")
        assert traffic.numeric_value == 1250000.0

    def test_커넥터_메타데이터(self):
        """커넥터 키와 표시명이 올바른지 확인."""
        assert self.connector.connector_key == "traffic_volume"
        assert "교통량" in self.connector.display_name

    @pytest.mark.asyncio
    async def test_fetch_API키_미설정(self):
        """API 키가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.traffic_volume.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = ""
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="DATA_GO_KR_API_KEY"):
                await self.connector.fetch({"year": "2023"})

    @pytest.mark.asyncio
    async def test_fetch_필수_파라미터_누락(self):
        """year가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.traffic_volume.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="year"):
                await self.connector.fetch({})

    @pytest.mark.asyncio
    async def test_fetch_정상_호출(self):
        """외부 API가 정상 응답을 반환할 때 데이터가 올바르게 반환되는지 확인."""
        mock_response = Response(
            status_code=200,
            json=self.SAMPLE_RESPONSE,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.traffic_volume.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await self.connector.fetch({"year": "2023", "dtype": "2"})
                assert result == self.SAMPLE_RESPONSE
                mock_client.get.assert_called_once()


# ──────────────────────────────────────────────────
# 행정안전부 생활쓰레기배출정보 커넥터 테스트
# ──────────────────────────────────────────────────


class TestWasteStatsConnector:
    """행정안전부 생활쓰레기배출정보 커넥터 단위 테스트."""

    def setup_method(self):
        self.connector = WasteStatsConnector()
        self.project_id = uuid.uuid4()
        self.data_source_id = uuid.uuid4()
        self.snapshot_id = uuid.uuid4()

    # 샘플 API 응답
    SAMPLE_RESPONSE = {
        "totalCount": 2,
        "data": [
            {
                "SGG_NM": "강남구",
                "DAT_CRTR_YMD": "20240315",
                "TOT_DSCG_QTY": "125.5",
                "FOOD_DSCG_QTY": "45.2",
                "RCYCLNG_QTY": "38.0",
            },
            {
                "SGG_NM": "강남구",
                "DAT_CRTR_YMD": "20240316",
                "TOT_DSCG_QTY": "130.0",
                "FOOD_DSCG_QTY": None,
                "RCYCLNG_QTY": "40.5",
            },
        ],
    }

    def test_normalize_정상_응답(self):
        """정상 응답에서 올바른 수의 증거가 생성되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        # 첫 번째: 생활폐기물 + 음식물쓰레기 + 재활용 = 3
        # 두 번째: 생활폐기물 + 재활용 = 2 (FOOD=None 건너뜀)
        assert len(evidences) == 5

    def test_normalize_폐기물_발생량_검증(self):
        """폐기물 발생량 지표 값과 단위가 올바르게 매핑되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        waste = next(e for e in evidences if e.indicator == "생활폐기물_발생량")
        assert waste.value == "125.5"
        assert waste.numeric_value == 125.5
        assert waste.unit == "톤/일"
        assert waste.category == EvidenceCategory.WASTE

    def test_normalize_음식물쓰레기(self):
        """음식물쓰레기 발생량이 올바르게 추출되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        food = [e for e in evidences if e.indicator == "음식물쓰레기_발생량"]
        assert len(food) == 1  # 두 번째 항목은 None이므로 건너뜀
        assert food[0].numeric_value == 45.2

    def test_normalize_재활용(self):
        """재활용 발생량이 올바르게 추출되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        recycle = [e for e in evidences if e.indicator == "재활용_발생량"]
        assert len(recycle) == 2

    def test_normalize_기준일_파싱(self):
        """YYYYMMDD 형식의 기준일이 올바르게 파싱되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        first = evidences[0]
        assert first.observed_at == datetime(2024, 3, 15)

    def test_normalize_메타데이터_포함(self):
        """메타데이터에 지역명과 기준일이 포함되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        first = evidences[0]
        assert first.metadata_json["region"] == "강남구"

    def test_normalize_빈_응답(self):
        """데이터가 없을 때 빈 리스트를 반환하는지 확인."""
        empty_payload = {"totalCount": 0, "data": []}
        evidences = self.connector.normalize(
            raw_payload=empty_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        assert evidences == []

    def test_normalize_screening_only_태깅(self):
        """screening_only 플래그가 올바르게 전달되는지 확인."""
        evidences = self.connector.normalize(
            raw_payload=self.SAMPLE_RESPONSE,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
            screening_only=True,
        )
        assert all(e.screening_only for e in evidences)

    def test_normalize_응답구조_패턴2(self):
        """response.body.items 패턴도 처리하는지 확인."""
        alt_payload = {
            "response": {
                "body": {
                    "items": [
                        {
                            "SGG_NM": "서초구",
                            "TOT_DSCG_QTY": "80.0",
                        },
                    ]
                }
            }
        }
        evidences = self.connector.normalize(
            raw_payload=alt_payload,
            project_id=self.project_id,
            data_source_id=self.data_source_id,
            snapshot_id=self.snapshot_id,
        )
        waste = [e for e in evidences if e.indicator == "생활폐기물_발생량"]
        assert len(waste) == 1
        assert waste[0].numeric_value == 80.0

    def test_커넥터_메타데이터(self):
        """커넥터 키와 표시명이 올바른지 확인."""
        assert self.connector.connector_key == "waste_stats"
        assert "쓰레기" in self.connector.display_name

    @pytest.mark.asyncio
    async def test_fetch_API키_미설정(self):
        """API 키가 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.waste_stats.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = ""
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="DATA_GO_KR_API_KEY"):
                await self.connector.fetch({"region": "강남구"})

    @pytest.mark.asyncio
    async def test_fetch_필수_파라미터_누락(self):
        """region이 없을 때 ValueError가 발생하는지 확인."""
        with patch("app.connectors.waste_stats.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with pytest.raises(ValueError, match="region"):
                await self.connector.fetch({})

    @pytest.mark.asyncio
    async def test_fetch_정상_호출(self):
        """외부 API가 정상 응답을 반환할 때 데이터가 올바르게 반환되는지 확인."""
        mock_response = Response(
            status_code=200,
            json=self.SAMPLE_RESPONSE,
            request=Request("GET", "http://test"),
        )

        with patch("app.connectors.waste_stats.settings") as mock_settings:
            mock_settings.DATA_GO_KR_API_KEY = "test_key"
            mock_settings.CONNECTOR_TIMEOUT = 30

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await self.connector.fetch({"region": "강남구"})
                assert result == self.SAMPLE_RESPONSE
                mock_client.get.assert_called_once()


# ──────────────────────────────────────────────────
# 커넥터 레지스트리 테스트
# ──────────────────────────────────────────────────


class TestConnectorRegistry:
    """커넥터 레지스트리 테스트."""

    def test_커넥터_등록_확인(self):
        """모든 커넥터가 레지스트리에 등록되어 있는지 확인."""
        assert "keco_air" in connector_registry
        assert "water_info" in connector_registry
        assert "soil_info" in connector_registry
        assert "kma_weather" in connector_registry
        assert "vworld_land_use" in connector_registry
        assert "cultural_heritage" in connector_registry
        assert "traffic_volume" in connector_registry
        assert "waste_stats" in connector_registry

    def test_커넥터_조회(self):
        """get_connector로 커넥터를 올바르게 조회할 수 있는지 확인."""
        from app.connectors.cultural_heritage import CulturalHeritageConnector
        from app.connectors.land_use import LandUseConnector

        air = get_connector("keco_air")
        assert air is not None
        assert isinstance(air, KecoAirConnector)

        water = get_connector("water_info")
        assert water is not None
        assert isinstance(water, WaterInfoConnector)

        soil = get_connector("soil_info")
        assert soil is not None
        assert isinstance(soil, SoilInfoConnector)

        weather = get_connector("kma_weather")
        assert weather is not None
        assert isinstance(weather, KmaWeatherConnector)

        land_use = get_connector("vworld_land_use")
        assert land_use is not None
        assert isinstance(land_use, LandUseConnector)

        heritage = get_connector("cultural_heritage")
        assert heritage is not None
        assert isinstance(heritage, CulturalHeritageConnector)

        traffic = get_connector("traffic_volume")
        assert traffic is not None
        assert isinstance(traffic, TrafficVolumeConnector)

        waste = get_connector("waste_stats")
        assert waste is not None
        assert isinstance(waste, WasteStatsConnector)

    def test_없는_커넥터_조회(self):
        """존재하지 않는 커넥터 키로 조회 시 None을 반환하는지 확인."""
        assert get_connector("nonexistent") is None

    def test_커넥터_메타데이터(self):
        """커넥터의 키와 표시명이 올바른지 확인."""
        air = get_connector("keco_air")
        assert air.connector_key == "keco_air"
        assert "에어코리아" in air.display_name

        water = get_connector("water_info")
        assert water.connector_key == "water_info"
        assert "수질" in water.display_name

        soil = get_connector("soil_info")
        assert soil.connector_key == "soil_info"
        assert "토양" in soil.display_name

        weather = get_connector("kma_weather")
        assert weather.connector_key == "kma_weather"
        assert "기상청" in weather.display_name

        land_use = get_connector("vworld_land_use")
        assert land_use.connector_key == "vworld_land_use"
        assert "토지이용" in land_use.display_name

        heritage = get_connector("cultural_heritage")
        assert heritage.connector_key == "cultural_heritage"
        assert "문화재" in heritage.display_name

        traffic = get_connector("traffic_volume")
        assert traffic.connector_key == "traffic_volume"
        assert "교통량" in traffic.display_name

        waste = get_connector("waste_stats")
        assert waste.connector_key == "waste_stats"
        assert "쓰레기" in waste.display_name


# ──────────────────────────────────────────────────
# 커넥터 수집 API 엔드포인트 테스트
# ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connectors_목록_조회(client):
    """GET /api/v1/connectors — 커넥터 목록을 조회한다."""
    resp = await client.get("/api/v1/connectors")
    assert resp.status_code == 200

    data = resp.json()
    keys = [c["connector_key"] for c in data]
    assert "keco_air" in keys
    assert "water_info" in keys
    assert "soil_info" in keys
    assert "kma_weather" in keys
    assert "traffic_volume" in keys
    assert "waste_stats" in keys


@pytest.mark.asyncio
async def test_존재하지_않는_커넥터_수집(client):
    """POST /api/v1/connectors/invalid/collect — 404 반환."""
    resp = await client.post(
        "/api/v1/connectors/nonexistent/collect",
        json={
            "project_id": str(uuid.uuid4()),
            "params": {},
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_에어코리아_수집_API키_누락(client, db_session):
    """에어코리아 수집 시 API 키가 없으면 에러 응답을 반환한다."""
    # 먼저 프로젝트 생성
    project_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "테스트 프로젝트",
            "description": "커넥터 테스트용",
        },
    )
    project_id = project_resp.json()["id"]

    # API 키 없이 수집 시도 — 502 또는 에러 스냅샷
    with patch("app.connectors.keco_air.settings") as mock_settings:
        mock_settings.DATA_GO_KR_API_KEY = ""
        mock_settings.CONNECTOR_TIMEOUT = 30

        resp = await client.post(
            "/api/v1/connectors/keco_air/collect",
            json={
                "project_id": project_id,
                "params": {"station_name": "종로구"},
            },
        )
        # collect()에서 fetch() 예외 → 에러 스냅샷 저장 → status=error 반환
        # BaseConnector.collect()가 예외를 잡아서 에러 스냅샷을 만드므로 200 응답
        assert resp.status_code == 200
        result = resp.json()
        assert result["status"] == "error"
        assert result["evidence_count"] == 0
