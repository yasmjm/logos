import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.client_ip import client_ip
from app.core.config import get_settings
from app.main import app
from tests.settings import TEST_SETTINGS


def _request(forwarded: str | None, peer: str = "10.0.0.5") -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded is not None else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


@pytest.mark.parametrize(
    ("forwarded", "hops", "expected"),
    [
        (None, 0, "10.0.0.5"),
        ("203.0.113.9", 0, "10.0.0.5"),  # hops=0: header ignored
        ("203.0.113.9", 1, "203.0.113.9"),  # proxy overwrote the header
        ("6.6.6.6, 203.0.113.9", 1, "203.0.113.9"),  # client forged the left part
        ("6.6.6.6, 203.0.113.9, 10.1.1.1", 2, "203.0.113.9"),
        (None, 1, "10.0.0.5"),  # no header: fall back to the peer
        ("203.0.113.9", 2, "10.0.0.5"),  # fewer hops than expected: do not guess
    ],
)
def test_client_ip_uses_the_entry_added_by_the_trusted_proxy(
    forwarded: str | None, hops: int, expected: str
) -> None:
    assert client_ip(_request(forwarded), hops) == expected


def test_forged_forwarded_for_does_not_bypass_login_limit(anon_client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS.model_copy(
        update={"trusted_proxy_hops": 1}
    )
    statuses = [
        anon_client.post(
            "/auth/login",
            data={"username": "ana", "password": "wrong"},
            # A fresh forged IP every time; the proxy-added entry stays the same.
            headers={"X-Forwarded-For": f"6.6.6.{i}, 198.51.100.1"},
        ).status_code
        for i in range(6)
    ]

    assert statuses == [401] * 5 + [429]


def test_distinct_real_clients_have_separate_login_limits(anon_client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS.model_copy(
        update={"trusted_proxy_hops": 1}
    )
    statuses = [
        anon_client.post(
            "/auth/login",
            data={"username": "ana", "password": "wrong"},
            headers={"X-Forwarded-For": f"198.51.100.{i}"},
        ).status_code
        for i in range(6)
    ]

    assert statuses == [401] * 6
