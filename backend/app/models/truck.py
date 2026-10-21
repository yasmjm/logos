from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import CargoType, ClientTier, string_enum


class Truck(Base):
    """Fleet registry. Incidents copy the cargo and client at creation time: the cargo
    changes every trip, and an incident must keep what was true when it happened."""

    __tablename__ = "trucks"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    cargo_type: Mapped[CargoType] = mapped_column(string_enum(CargoType, "cargo_type"))
    client_name: Mapped[str] = mapped_column(String(120))
    client_tier: Mapped[ClientTier] = mapped_column(string_enum(ClientTier, "client_tier"))
