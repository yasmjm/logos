from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.sla import ESCALATION_MINUTES, SLA_MINUTES
from app.main import app
from tests.settings import TEST_SETTINGS

# --- /config --------------------------------------------------------------------------


def test_config_exposes_rules_from_the_single_source(client: TestClient) -> None:
    body = client.get("/config").json()

    assert body["sla_minutes"] == {s.value: m for s, m in SLA_MINUTES.items()}
    assert body["sla_minutes"] == {"high": 5, "medium": 15, "low": 30}
    assert body["escalation_minutes"] == ESCALATION_MINUTES == 5
    assert body["features"] == {"demo": False, "chaos": False}


def test_config_reports_enabled_tools(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS.model_copy(
        update={"demo_mode": True, "chaos_enabled": True}
    )

    assert client.get("/config").json()["features"] == {"demo": True, "chaos": True}


def test_config_requires_authentication(anon_client: TestClient) -> None:
    assert anon_client.get("/config").status_code == 401
