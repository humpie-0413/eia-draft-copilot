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

from app.connectors.keco_air import KecoAirConnector
from app.connectors.kma_weather import KmaWeatherConnector
from app.connectors.soil_info import SoilInfoConnector
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

    def test_커넥터_조회(self):
        """get_connector로 커넥터를 올바르게 조회할 수 있는지 확인."""
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
