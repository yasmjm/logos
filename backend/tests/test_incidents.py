import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import IncidentCategory, IncidentStatus, Severity
from tests.factories import auth_headers, make_analyst, make_event, make_incident

PROBLEM_JSON = "application/problem+json"


def _ids(response) -> list[str]:
    return [item["id"] for item in response.json()["items"]]


# --- pagination -----------------------------------------------------------------------


def test_pagination_returns_total_and_slices(client: TestClient, db: Session) -> None:
    for minutes in range(5):
        make_incident(db, age=timedelta(minutes=minutes))

    page = client.get("/incidents", params={"limit": 2, "offset": 2}).json()

    assert page["total"] == 5
    assert page["limit"] == 2
    assert page["offset"] == 2
    assert len(page["items"]) == 2


# --- filters --------------------------------------------------------------------------


def test_filters_combine_multiple_values(client: TestClient, db: Session) -> None:
    match_high = make_incident(
        db, severity=Severity.HIGH, category=IncidentCategory.VEHICLE_ACCIDENT
    )
    match_medium = make_incident(
        db,
        severity=Severity.MEDIUM,
        category=IncidentCategory.ROAD_BLOCKAGE,
        status=IncidentStatus.INVESTIGATING,
    )
    make_incident(db, severity=Severity.LOW, category=IncidentCategory.VEHICLE_ACCIDENT)
    make_incident(db, severity=Severity.HIGH, category=IncidentCategory.ADVERSE_WEATHER)
    make_incident(
        db,
        severity=Severity.HIGH,
        category=IncidentCategory.VEHICLE_ACCIDENT,
        status=IncidentStatus.CLOSED,
    )

    response = client.get(
        "/incidents",
        params={
            "severity": ["high", "medium"],
            "category": ["vehicle_accident", "road_blockage"],
            "status": ["open", "investigating"],
        },
    )

    assert response.status_code == 200
    assert set(_ids(response)) == {str(match_high.id), str(match_medium.id)}
    assert response.json()["total"] == 2


def test_assigned_to_me_uses_the_token_analyst(client: TestClient, db: Session) -> None:
    ana = make_analyst(db, "ana", "Ana Souza")
    bruno = make_analyst(db, "bruno", "Bruno Lima")
    mine = make_incident(db, status=IncidentStatus.INVESTIGATING, assigned_to=ana.id)
    make_incident(db, status=IncidentStatus.INVESTIGATING, assigned_to=bruno.id)
    make_incident(db)

    response = client.get("/incidents", params={"assigned_to": "me"}, headers=auth_headers(ana))

    assert _ids(response) == [str(mine.id)]
    assert response.json()["items"][0]["assignee"] == {"id": str(ana.id), "name": "Ana Souza"}


# --- soft delete ----------------------------------------------------------------------


def test_soft_deleted_incidents_are_hidden_everywhere(client: TestClient, db: Session) -> None:
    visible = make_incident(db)
    deleted = make_incident(
        db, severity=Severity.HIGH, deleted_at=datetime.now(UTC) - timedelta(minutes=1)
    )

    listing = client.get("/incidents").json()
    assert [i["id"] for i in listing["items"]] == [str(visible.id)]
    assert listing["total"] == 1

    assert client.get(f"/incidents/{deleted.id}").status_code == 404

    summary = client.get("/incidents/summary").json()
    assert summary["total_active"] == 1
    assert summary["by_severity"]["high"] == 0


# --- detail and summary ---------------------------------------------------------------


def test_detail_returns_timeline_in_chronological_order(client: TestClient, db: Session) -> None:
    ana = make_analyst(db)
    created_at = datetime.now(UTC) - timedelta(hours=1)
    incident = make_incident(db, status=IncidentStatus.CLOSED, created_at=created_at)
    # Inserted out of order on purpose.
    make_event(
        db,
        incident,
        from_status=IncidentStatus.INVESTIGATING,
        to_status=IncidentStatus.CLOSED,
        at=created_at + timedelta(minutes=40),
        analyst=ana,
    )
    make_event(db, incident, to_status=IncidentStatus.OPEN, at=created_at)
    make_event(
        db,
        incident,
        from_status=IncidentStatus.OPEN,
        to_status=IncidentStatus.INVESTIGATING,
        at=created_at + timedelta(minutes=5),
        analyst=ana,
    )

    response = client.get(f"/incidents/{incident.id}")

    assert response.status_code == 200
    events = response.json()["events"]
    assert [e["to_status"] for e in events] == ["open", "investigating", "closed"]
    assert events[0]["analyst"] is None
    assert events[1]["analyst"]["name"] == "Ana Souza"


def test_detail_timeline_includes_event_note(client: TestClient, db: Session) -> None:
    ana = make_analyst(db)
    incident = make_incident(db, status=IncidentStatus.INCONCLUSIVE)
    make_event(
        db,
        incident,
        from_status=IncidentStatus.INVESTIGATING,
        to_status=IncidentStatus.INCONCLUSIVE,
        at=datetime.now(UTC),
        analyst=ana,
        note="Motorista não atendeu nenhuma ligação.",
    )

    events = client.get(f"/incidents/{incident.id}").json()["events"]

    assert events[0]["note"] == "Motorista não atendeu nenhuma ligação."


def test_missing_location_is_null_not_empty_string(client: TestClient, db: Session) -> None:
    incident = make_incident(db, highway=None, km=None, location_note="")

    item = client.get(f"/incidents/{incident.id}").json()

    assert item["highway"] is None
    assert item["km"] is None
    assert item["location_note"] is None


def test_summary_counts_only_active_incidents(client: TestClient, db: Session) -> None:
    make_incident(db, severity=Severity.HIGH, category=IncidentCategory.ROAD_BLOCKAGE)
    make_incident(
        db,
        severity=Severity.HIGH,
        category=IncidentCategory.ROAD_BLOCKAGE,
        status=IncidentStatus.INVESTIGATING,
    )
    make_incident(db, severity=Severity.LOW, status=IncidentStatus.CLOSED)
    make_incident(db, severity=Severity.LOW, status=IncidentStatus.INCONCLUSIVE)

    summary = client.get("/incidents/summary").json()

    assert summary["total_active"] == 2
    assert summary["by_severity"] == {"high": 2, "medium": 0, "low": 0}
    assert summary["by_category"]["road_blockage"] == 2
    assert sum(summary["by_category"].values()) == 2


# --- errors ---------------------------------------------------------------------------


def test_unknown_incident_returns_404_problem(client: TestClient) -> None:
    incident_id = uuid.uuid4()

    response = client.get(f"/incidents/{incident_id}")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": f"Incident {incident_id} not found.",
    }


def test_invalid_filter_returns_422_problem(client: TestClient) -> None:
    response = client.get("/incidents", params={"severity": ["high", "urgent"]})

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert body["status"] == 422
    assert "query parameter 'severity'" in body["detail"]
    assert "'urgent'" in body["detail"]


def test_limit_above_maximum_returns_422(client: TestClient) -> None:
    response = client.get("/incidents", params={"limit": 201})

    assert response.status_code == 422
    assert "query parameter 'limit'" in response.json()["detail"]


def test_invalid_incident_id_returns_422(client: TestClient) -> None:
    response = client.get("/incidents/not-a-uuid")

    assert response.status_code == 422
    assert "path parameter 'incident_id'" in response.json()["detail"]
