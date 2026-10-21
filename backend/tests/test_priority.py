"""Business-impact priority (app/domain/priority.py), computed by the database."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Analyst, CargoType, ClientTier, IncidentCategory, IncidentStatus, Severity
from tests.factories import make_incident

C = IncidentCategory
S = Severity


def _items(client: TestClient) -> list[dict]:
    return client.get("/incidents").json()["items"]


def _by_id(client: TestClient) -> dict[str, dict]:
    return {item["id"]: item for item in _items(client)}


def test_flat_tire_with_perishable_cargo_of_strategic_client_beats_a_scrape(
    client: TestClient, db: Session
) -> None:
    flat_tire = make_incident(
        db,
        category=C.MECHANICAL_FAILURE,
        severity=S.LOW,
        cargo_type=CargoType.PERISHABLE,
        client_tier=ClientTier.STRATEGIC,
    )
    scrape = make_incident(
        db,
        category=C.VEHICLE_ACCIDENT,
        severity=S.LOW,
        cargo_type=CargoType.GENERAL,
        client_tier=ClientTier.STANDARD,
    )

    items = _items(client)

    assert [i["id"] for i in items] == [str(flat_tire.id), str(scrape.id)]
    # (2×90 + 1.5×20 + 1×100) / 4.5 = 68.9 → 69;  (2×40 + 1.5×35 + 1×40) / 4.5 = 38.3 → 38
    assert [i["priority_score"] for i in items] == [69, 38]
    assert items[0]["priority_breakdown"] == {
        "cargo_points": 90,
        "problem_points": 20,
        "client_points": 100,
        "base": 68.9,
        "wait_bonus": 0,
        "victims": False,
    }


def test_active_victims_are_always_first_oldest_first(client: TestClient, db: Session) -> None:
    worst_without_victims = make_incident(
        db,
        category=C.VEHICLE_ACCIDENT,
        severity=S.HIGH,
        cargo_type=CargoType.HAZARDOUS,
        client_tier=ClientTier.STRATEGIC,
        age=timedelta(hours=1),  # +20 waiting bonus: 95 + 20 = 115
    )
    newer_victims = make_incident(db, category=C.ACCIDENT_WITH_VICTIMS, severity=S.LOW)
    older_victims = make_incident(
        db, category=C.ACCIDENT_WITH_VICTIMS, severity=S.LOW, age=timedelta(minutes=3)
    )

    items = _items(client)

    assert [i["id"] for i in items] == [
        str(older_victims.id),
        str(newer_victims.id),
        str(worst_without_victims.id),
    ]
    assert [i["priority_score"] for i in items] == [200, 200, 115]
    assert items[0]["priority_breakdown"]["victims"] is True


def test_resolved_victims_lose_the_override_and_go_last(
    client: TestClient, db: Session, current_analyst: Analyst
) -> None:
    resolved_victims = make_incident(
        db,
        category=C.ACCIDENT_WITH_VICTIMS,
        status=IncidentStatus.CLOSED,
        assigned_to=current_analyst.id,
    )
    open_low = make_incident(db)

    items = _items_with_closed(client)

    assert [i["id"] for i in items] == [str(open_low.id), str(resolved_victims.id)]
    assert items[1]["priority_breakdown"]["victims"] is False


def _items_with_closed(client: TestClient) -> list[dict]:
    return client.get("/incidents", params={"status": ["open", "closed"]}).json()["items"]


def test_waiting_bonus_one_per_minute_capped_at_20(client: TestClient, db: Session) -> None:
    fresh = make_incident(db)
    waiting_12 = make_incident(db, age=timedelta(minutes=12))
    waiting_3h = make_incident(db, age=timedelta(hours=3))

    items = _by_id(client)

    base = 33  # general 40, standard 40, mechanical low 20 → 33.3
    assert items[str(fresh.id)]["priority_breakdown"]["wait_bonus"] == 0
    assert items[str(waiting_12.id)]["priority_breakdown"]["wait_bonus"] == 12
    assert items[str(waiting_3h.id)]["priority_breakdown"]["wait_bonus"] == 20
    assert items[str(waiting_3h.id)]["priority_score"] == base + 20


def test_waiting_bonus_freezes_when_someone_takes_it(
    client: TestClient, db: Session, current_analyst: Analyst
) -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=50, seconds=30)
    taken = make_incident(
        db,
        status=IncidentStatus.INVESTIGATING,
        assigned_to=current_analyst.id,
        created_at=created_at,
        acknowledged_at=created_at + timedelta(minutes=7, seconds=10),
    )

    item = _by_id(client)[str(taken.id)]

    assert item["priority_breakdown"]["wait_bonus"] == 7
    assert item["priority_score"] == 33 + 7


def test_unknown_truck_is_scored_as_general_cargo_and_standard_client(
    client: TestClient, db: Session
) -> None:
    unknown = make_incident(db, fleet_match=False)  # defaults: general / standard

    item = _by_id(client)[str(unknown.id)]

    assert item["fleet_match"] is False
    assert item["priority_breakdown"]["cargo_points"] == 40
    assert item["priority_breakdown"]["client_points"] == 40


def test_detail_has_the_same_score_and_breakdown_as_the_list(
    client: TestClient, db: Session
) -> None:
    incident = make_incident(db, cargo_type=CargoType.HIGH_VALUE, client_tier=ClientTier.PRIORITY)

    listed = _by_id(client)[str(incident.id)]
    detail = client.get(f"/incidents/{incident.id}").json()

    assert detail["priority_score"] == listed["priority_score"]
    assert detail["priority_breakdown"] == listed["priority_breakdown"]


def test_config_exposes_weights_and_tables(client: TestClient) -> None:
    priority = client.get("/config").json()["priority"]

    assert priority["weights"] == {"cargo": 2.0, "problem": 1.5, "client": 1.0}
    assert priority["cargo_points"]["perishable"] == 90
    assert priority["problem_points"]["vehicle_accident"] == {"high": 85, "medium": 60, "low": 35}
    assert priority["client_points"]["strategic"] == 100
    assert priority["wait_bonus_cap"] == 20
    assert priority["victims_score"] == 200
