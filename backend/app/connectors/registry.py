"""커넥터 레지스트리.

connector_key → BaseConnector 인스턴스를 매핑한다.
새 커넥터 추가 시 이 모듈에 등록하면 된다.
"""

from app.connectors.base import BaseConnector

# 커넥터 키 → 인스턴스 매핑
connector_registry: dict[str, BaseConnector] = {}


def register_connector(connector: BaseConnector) -> None:
    """커넥터를 레지스트리에 등록한다."""
    connector_registry[connector.connector_key] = connector


def get_connector(connector_key: str) -> BaseConnector | None:
    """커넥터 키로 커넥터 인스턴스를 조회한다."""
    return connector_registry.get(connector_key)


def _register_all() -> None:
    """모든 커넥터를 레지스트리에 등록한다. 앱 시작 시 호출."""
    from app.connectors.keco_air import KecoAirConnector
    from app.connectors.water_info import WaterInfoConnector

    register_connector(KecoAirConnector())
    register_connector(WaterInfoConnector())


# 모듈 로드 시 자동 등록
_register_all()
