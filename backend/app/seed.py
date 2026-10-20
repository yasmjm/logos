"""Seed the local database with analysts and realistic incidents.

Usage: uv run python -m app.seed

Idempotent: truncates analysts, incidents and incident_events, then recreates
everything. Timestamps are relative to the moment of execution (last 6 hours).
"""

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Analyst,
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentSource,
    IncidentStatus,
    Severity,
)

TOTAL_INCIDENTS = 120
SEVERITY_COUNTS = {Severity.HIGH: 18, Severity.MEDIUM: 54, Severity.LOW: 48}
INVESTIGATING_COUNT = 20
CLOSED_COUNT = 12
INCONCLUSIVE_COUNT = 3
WINDOW = timedelta(hours=6)
WHATSAPP_RATIO = 0.3
# WhatsApp reports where the driver did not say where they are.
WHATSAPP_WITHOUT_LOCATION_COUNT = 5
DEFAULT_PASSWORD = "logos123"

ANALYSTS = [("Ana Souza", "ana"), ("Bruno Lima", "bruno")]


@dataclass(frozen=True)
class Stretch:
    highway: str
    km_min: int
    km_max: int
    places: tuple[str, ...]


STRETCHES = [
    Stretch(
        "BR-116",
        100,
        480,
        (
            "Régis Bittencourt, próximo a Registro/SP",
            "Serra do Cafezal, Miracatu/SP",
            "Juquitiba/SP",
        ),
    ),
    Stretch(
        "BR-116",
        140,
        230,
        (
            "Via Dutra, Guaratinguetá/SP",
            "Via Dutra, Resende/RJ",
            "Via Dutra, São José dos Campos/SP",
        ),
    ),
    Stretch("BR-101", 100, 250, ("Joinville/SC", "Itajaí/SC", "Palhoça/SC")),
    Stretch("BR-101", 380, 470, ("Campos dos Goytacazes/RJ", "Rio Bonito/RJ")),
    Stretch(
        "BR-163", 300, 850, ("Sinop/MT", "Lucas do Rio Verde/MT", "Sorriso/MT", "Nova Mutum/MT")
    ),
    Stretch(
        "BR-381",
        400,
        560,
        ("Fernão Dias, Betim/MG", "Fernão Dias, Pouso Alegre/MG", "Fernão Dias, Extrema/MG"),
    ),
    Stretch("BR-040", 500, 800, ("Sete Lagoas/MG", "Conselheiro Lafaiete/MG", "Juiz de Fora/MG")),
    Stretch(
        "SP-330",
        20,
        330,
        ("Anhanguera, Jundiaí/SP", "Anhanguera, Campinas/SP", "Anhanguera, Ribeirão Preto/SP"),
    ),
    Stretch("SP-348", 20, 150, ("Bandeirantes, Cajamar/SP", "Bandeirantes, Limeira/SP")),
    Stretch(
        "BR-153",
        100,
        450,
        ("Transbrasiliana, Anápolis/GO", "Transbrasiliana, São José do Rio Preto/SP"),
    ),
    Stretch("BR-277", 50, 600, ("Curitiba/PR", "Guarapuava/PR", "Cascavel/PR")),
]

DESCRIPTIONS = {
    IncidentCategory.VEHICLE_ACCIDENT: [
        "Colisão traseira com veículo de passeio; motorista sem ferimentos, carga íntegra.",
        "Caminhão tombou no acostamento após manobra evasiva; carga parcialmente avariada.",
        "Engavetamento envolvendo três veículos; caminhão com danos na lateral.",
        "Saída de pista em curva acentuada; veículo parado no canteiro.",
        "Raspão em ônibus durante ultrapassagem; danos leves no retrovisor.",
    ],
    IncidentCategory.ACCIDENT_WITH_VICTIMS: [
        "Colisão frontal com carro de passeio; duas vítimas, SAMU acionado.",
        "Atropelamento de pedestre na faixa; motorista em choque, PRF no local.",
        "Motorista ferido após tombamento; aguardando resgate do Corpo de Bombeiros.",
        "Colisão com motocicleta; motociclista com ferimentos graves.",
    ],
    IncidentCategory.ADVERSE_WEATHER: [
        "Neblina intensa com visibilidade abaixo de 50 metros; motorista parado em posto.",
        "Chuva forte e acúmulo de água na pista; velocidade reduzida a 30 km/h.",
        "Alagamento no trecho; caminhão aguardando escoamento para seguir viagem.",
        "Rajadas de vento fortes com risco de tombamento; carga alta.",
        "Granizo na região; para-brisa trincado, motorista seguro.",
    ],
    IncidentCategory.MECHANICAL_FAILURE: [
        "Pneu estourado no eixo traseiro; aguardando borracharia.",
        "Superaquecimento do motor; caminhão parado no acostamento.",
        "Falha no sistema de freios detectada no painel; veículo imobilizado.",
        "Pane elétrica; caminhão sem iluminação, triângulo sinalizado.",
        "Vazamento de óleo hidráulico; guincho solicitado.",
        "Embreagem patinando; motorista sem conseguir subir a serra.",
    ],
    IncidentCategory.ROAD_BLOCKAGE: [
        "Pista totalmente interditada por manifestação; fila de 5 km.",
        "Deslizamento de terra bloqueando duas faixas; desvio indicado pela PRF.",
        "Interdição para remoção de carreta tombada; previsão de liberação em 2 horas.",
        "Obras na pista com sistema pare-e-siga; espera de 40 minutos.",
        "Queda de árvore bloqueando a faixa da direita.",
    ],
}

# Which categories are plausible for each severity.
CATEGORIES_BY_SEVERITY = {
    Severity.HIGH: [
        IncidentCategory.ACCIDENT_WITH_VICTIMS,
        IncidentCategory.ACCIDENT_WITH_VICTIMS,
        IncidentCategory.VEHICLE_ACCIDENT,
        IncidentCategory.ROAD_BLOCKAGE,
    ],
    Severity.MEDIUM: [
        IncidentCategory.VEHICLE_ACCIDENT,
        IncidentCategory.MECHANICAL_FAILURE,
        IncidentCategory.ADVERSE_WEATHER,
        IncidentCategory.ROAD_BLOCKAGE,
    ],
    Severity.LOW: [
        IncidentCategory.MECHANICAL_FAILURE,
        IncidentCategory.MECHANICAL_FAILURE,
        IncidentCategory.ADVERSE_WEATHER,
        IncidentCategory.ROAD_BLOCKAGE,
    ],
}

FIRST_NAMES = [
    "João",
    "José",
    "Carlos",
    "Paulo",
    "Marcos",
    "Antônio",
    "Luiz",
    "Rafael",
    "Sérgio",
    "Edson",
    "Valdir",
    "Cláudio",
    "Roberto",
    "Adriano",
    "Márcia",
    "Rosana",
    "Daniela",
]
LAST_NAMES = [
    "Silva",
    "Santos",
    "Oliveira",
    "Pereira",
    "Ferreira",
    "Almeida",
    "Costa",
    "Rodrigues",
    "Gomes",
    "Martins",
    "Ribeiro",
    "Carvalho",
    "Barbosa",
    "Rocha",
    "Nascimento",
]

WHATSAPP_OPENERS = ["Central,", "Boa tarde central,", "Oi central", "Bom dia,", "Central, urgente:"]


def _whatsapp_message(
    rng: random.Random, truck_code: str, location: str | None, description: str
) -> str:
    opener = rng.choice(WHATSAPP_OPENERS)
    where = f", to na {location}" if location else ""
    return f"{opener} aqui é o {truck_code}{where}. {description.lower()}"


def _build_incidents(
    rng: random.Random,
    now: datetime,
    analysts: list[Analyst],
) -> tuple[list[Incident], list[IncidentEvent]]:
    severities = [sev for sev, count in SEVERITY_COUNTS.items() for _ in range(count)]
    rng.shuffle(severities)

    incidents: list[Incident] = []
    for severity in severities:
        category = rng.choice(CATEGORIES_BY_SEVERITY[severity])
        stretch = rng.choice(STRETCHES)
        km = Decimal(rng.randint(stretch.km_min * 10, stretch.km_max * 10)) / 10
        truck_code = f"TRK-{rng.randint(1, 5000):04d}"
        description = rng.choice(DESCRIPTIONS[category])
        source = IncidentSource.WHATSAPP if rng.random() < WHATSAPP_RATIO else IncidentSource.API
        created_at = now - timedelta(seconds=rng.uniform(0, WINDOW.total_seconds()))
        incidents.append(
            Incident(
                id=uuid.uuid4(),
                description=description,
                category=category,
                severity=severity,
                status=IncidentStatus.OPEN,
                truck_code=truck_code,
                driver_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                highway=stretch.highway,
                km=km,
                location_note=rng.choice(stretch.places),
                source=source,
                raw_message=(
                    _whatsapp_message(rng, truck_code, f"{stretch.highway} km {km}", description)
                    if source is IncidentSource.WHATSAPP
                    else None
                ),
                version=1,
                created_at=created_at,
                updated_at=created_at,
            )
        )

    whatsapp = [i for i in incidents if i.source is IncidentSource.WHATSAPP]
    for incident in rng.sample(whatsapp, WHATSAPP_WITHOUT_LOCATION_COUNT):
        incident.highway = None
        incident.km = None
        incident.location_note = None
        incident.raw_message = _whatsapp_message(
            rng, incident.truck_code, None, incident.description
        )

    # Older incidents are the ones the team already had time to handle.
    oldest_first = sorted(incidents, key=lambda i: i.created_at)
    resolved_pool = [i for i in oldest_first if now - i.created_at > timedelta(hours=2)]
    resolved = rng.sample(resolved_pool, CLOSED_COUNT + INCONCLUSIVE_COUNT)
    investigating_pool = [
        i for i in oldest_first if now - i.created_at > timedelta(minutes=30) and i not in resolved
    ]
    investigating = rng.sample(investigating_pool, INVESTIGATING_COUNT)

    events: list[IncidentEvent] = []
    for incident in incidents:
        events.append(
            IncidentEvent(
                incident_id=incident.id,
                event_type=IncidentEventType.CREATED,
                from_status=None,
                to_status=IncidentStatus.OPEN,
                created_at=incident.created_at,
            )
        )

    final_statuses = (
        [(i, IncidentStatus.INVESTIGATING) for i in investigating]
        + [(i, IncidentStatus.CLOSED) for i in resolved[:CLOSED_COUNT]]
        + [(i, IncidentStatus.INCONCLUSIVE) for i in resolved[CLOSED_COUNT:]]
    )
    for incident, final_status in final_statuses:
        analyst = rng.choice(analysts)
        acknowledged_at = incident.created_at + timedelta(minutes=rng.uniform(2, 25))
        incident.status = IncidentStatus.INVESTIGATING
        incident.assigned_to = analyst.id
        incident.acknowledged_at = acknowledged_at
        incident.version += 1
        incident.updated_at = acknowledged_at
        events.append(
            IncidentEvent(
                incident_id=incident.id,
                analyst_id=analyst.id,
                event_type=IncidentEventType.STATUS_CHANGED,
                from_status=IncidentStatus.OPEN,
                to_status=IncidentStatus.INVESTIGATING,
                created_at=acknowledged_at,
            )
        )

        if final_status is IncidentStatus.INVESTIGATING:
            continue

        resolved_at = min(
            acknowledged_at + timedelta(minutes=rng.uniform(15, 120)),
            now - timedelta(minutes=1),
        )
        incident.status = final_status
        incident.resolved_at = resolved_at
        incident.version += 1
        incident.updated_at = resolved_at
        events.append(
            IncidentEvent(
                incident_id=incident.id,
                analyst_id=analyst.id,
                event_type=IncidentEventType.STATUS_CHANGED,
                from_status=IncidentStatus.INVESTIGATING,
                to_status=final_status,
                created_at=resolved_at,
            )
        )

    return incidents, events


def seed(db: Session) -> None:
    rng = random.Random(42)
    now = datetime.now(UTC)

    # Listing all three tables in one TRUNCATE satisfies the RESTRICT foreign keys.
    db.execute(text("TRUNCATE incident_events, incidents, analysts"))

    analysts = [
        Analyst(
            id=uuid.uuid4(),
            name=name,
            username=username,
            password_hash=hash_password(DEFAULT_PASSWORD),
            created_at=now - WINDOW,
        )
        for name, username in ANALYSTS
    ]
    db.add_all(analysts)
    db.flush()

    incidents, events = _build_incidents(rng, now, analysts)
    db.add_all(incidents)
    db.flush()
    db.add_all(events)


def main() -> None:
    with SessionLocal() as db, db.begin():
        seed(db)
        counts = db.execute(
            text("SELECT status, severity, count(*) FROM incidents GROUP BY 1, 2 ORDER BY 1, 2")
        ).all()
    print("Seed concluído:")
    for status, severity, count in counts:
        print(f"  {status:<14} {severity:<7} {count}")


if __name__ == "__main__":
    main()
