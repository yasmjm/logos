from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.models import CargoType, ClientTier, Truck


@dataclass(frozen=True)
class FleetSnapshot:
    cargo_type: CargoType
    client_name: str | None
    client_tier: ClientTier
    fleet_match: bool

    def as_fields(self) -> dict:
        return asdict(self)


# Unknown truck: neutral defaults, flagged so the analyst knows the data is missing.
UNKNOWN_TRUCK = FleetSnapshot(
    cargo_type=CargoType.GENERAL,
    client_name=None,
    client_tier=ClientTier.STANDARD,
    fleet_match=False,
)


def snapshot_of(truck: Truck | None) -> FleetSnapshot:
    if truck is None:
        return UNKNOWN_TRUCK
    return FleetSnapshot(truck.cargo_type, truck.client_name, truck.client_tier, fleet_match=True)


def snapshot_fleet(db: Session, truck_code: str) -> FleetSnapshot:
    """What the fleet says about this truck right now, to be COPIED into the incident."""
    return snapshot_of(db.get(Truck, truck_code))
