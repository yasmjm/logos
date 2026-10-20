"""Demo data: analysts and realistic incidents, reused by the CLI and by /demo.

CLI (local development only): uv run python -m app.seed

The CLI WIPES incidents and incident_events with TRUNCATE, then recreates the
incidents with timestamps relative to now (last 6 hours). This deletes audit
history on purpose and must never run against a shared or production database.
Analysts are kept with the same ids (created only if missing), so tokens issued
before the seed keep working.

The API never deletes history: POST /demo/reset soft-deletes instead
(see app/services/demo.py).
"""

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
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


@dataclass(frozen=True)
class Template:
    category: IncidentCategory
    severity: Severity
    description: str


# Each description has a fixed, coherent severity. The seed draws the severity first
# (to keep the target distribution) and then a template with that severity.
_C = IncidentCategory
_S = Severity
TEMPLATES = [
    # vehicle_accident
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.LOW,
        "Raspão em ônibus durante ultrapassagem; danos leves no retrovisor.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.LOW,
        "Batida leve em manobra no pátio do posto; para-choque amassado.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.LOW,
        "Retrovisor quebrado por galho em trecho estreito; viagem segue normalmente.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.MEDIUM,
        "Colisão traseira com veículo de passeio em baixa velocidade; sem feridos, carga íntegra.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.MEDIUM,
        "Engavetamento envolvendo três veículos; caminhão com danos na lateral, sem feridos.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.MEDIUM,
        "Saída de pista em curva acentuada; veículo parado no canteiro central.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.MEDIUM,
        "Colisão com animal na pista; radiador danificado, veículo sem condições de seguir.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.HIGH,
        "Caminhão tombou no acostamento após manobra evasiva; carga parcialmente avariada.",
    ),
    Template(
        _C.VEHICLE_ACCIDENT,
        _S.HIGH,
        "Carreta tombada atravessada na pista com carga de combustível; risco de vazamento.",
    ),
    # accident_with_victims
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.MEDIUM,
        "Motorista com corte no braço após colisão leve; atendido no local, sem remoção.",
    ),
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.MEDIUM,
        "Ocupante do outro veículo com escoriações leves; recusou atendimento médico.",
    ),
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.HIGH,
        "Colisão frontal com carro de passeio; duas vítimas, SAMU acionado.",
    ),
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.HIGH,
        "Atropelamento de pedestre na faixa; motorista em choque, PRF no local.",
    ),
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.HIGH,
        "Motorista ferido após tombamento; aguardando resgate do Corpo de Bombeiros.",
    ),
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.HIGH,
        "Colisão com motocicleta; motociclista com ferimentos graves.",
    ),
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.HIGH,
        "Vítima presa às ferragens após colisão lateral; resgate a caminho.",
    ),
    Template(
        _C.ACCIDENT_WITH_VICTIMS,
        _S.HIGH,
        "Motorista desacordado após colisão com mureta; SAMU acionado.",
    ),
    # adverse_weather
    Template(
        _C.ADVERSE_WEATHER,
        _S.LOW,
        "Chuva forte e acúmulo de água na pista; velocidade reduzida a 30 km/h.",
    ),
    Template(
        _C.ADVERSE_WEATHER, _S.LOW, "Granizo na região; para-brisa trincado, motorista seguro."
    ),
    Template(
        _C.ADVERSE_WEATHER,
        _S.LOW,
        "Chuva fina e pista escorregadia; motorista reduziu a velocidade por precaução.",
    ),
    Template(_C.ADVERSE_WEATHER, _S.LOW, "Serração leve no amanhecer; tráfego lento, mas fluindo."),
    Template(
        _C.ADVERSE_WEATHER,
        _S.LOW,
        "Temporal com semáforos apagados no perímetro urbano; trânsito lento.",
    ),
    Template(
        _C.ADVERSE_WEATHER,
        _S.MEDIUM,
        "Neblina intensa com visibilidade abaixo de 50 metros; motorista parado em posto.",
    ),
    Template(
        _C.ADVERSE_WEATHER,
        _S.MEDIUM,
        "Alagamento no trecho; caminhão aguardando escoamento para seguir viagem.",
    ),
    Template(
        _C.ADVERSE_WEATHER,
        _S.MEDIUM,
        "Rajadas de vento fortes com risco de tombamento; carga alta, motorista parado.",
    ),
    Template(
        _C.ADVERSE_WEATHER,
        _S.HIGH,
        "Enxurrada arrastando lama para a pista em trecho de serra; risco de deslizamento.",
    ),
    # mechanical_failure
    Template(
        _C.MECHANICAL_FAILURE, _S.LOW, "Pneu estourado no eixo traseiro; aguardando borracharia."
    ),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.LOW,
        "Luz de injeção acesa no painel; motorista seguindo até a próxima oficina.",
    ),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.LOW,
        "Lanterna traseira queimada; troca prevista na próxima parada.",
    ),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.LOW,
        "Bateria descarregada no posto de abastecimento; aguardando carga.",
    ),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.MEDIUM,
        "Superaquecimento do motor; caminhão parado no acostamento.",
    ),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.MEDIUM,
        "Falha no sistema de freios detectada no painel; veículo imobilizado no acostamento.",
    ),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.MEDIUM,
        "Pane elétrica à noite; caminhão sem iluminação, triângulo sinalizado.",
    ),
    Template(_C.MECHANICAL_FAILURE, _S.MEDIUM, "Vazamento de óleo hidráulico; guincho solicitado."),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.MEDIUM,
        "Embreagem patinando; motorista sem conseguir subir a serra.",
    ),
    Template(
        _C.MECHANICAL_FAILURE,
        _S.HIGH,
        "Perda parcial de freio em descida de serra; motorista usou a área de escape.",
    ),
    # road_blockage
    Template(
        _C.ROAD_BLOCKAGE, _S.LOW, "Obras na pista com sistema pare-e-siga; espera de 40 minutos."
    ),
    Template(
        _C.ROAD_BLOCKAGE,
        _S.LOW,
        "Queda de árvore bloqueando a faixa da direita; fluxo pela esquerda.",
    ),
    Template(
        _C.ROAD_BLOCKAGE,
        _S.LOW,
        "Fiscalização da PRF com fila de caminhões; espera estimada de 20 minutos.",
    ),
    Template(
        _C.ROAD_BLOCKAGE, _S.MEDIUM, "Pista totalmente interditada por manifestação; fila de 5 km."
    ),
    Template(
        _C.ROAD_BLOCKAGE,
        _S.MEDIUM,
        "Interdição para remoção de carreta tombada; previsão de liberação em 2 horas.",
    ),
    Template(
        _C.ROAD_BLOCKAGE,
        _S.MEDIUM,
        "Ponte com interdição parcial após vistoria; apenas uma faixa liberada.",
    ),
    Template(
        _C.ROAD_BLOCKAGE,
        _S.HIGH,
        "Deslizamento de terra bloqueando duas faixas; desvio indicado pela PRF.",
    ),
    Template(
        _C.ROAD_BLOCKAGE,
        _S.HIGH,
        "Incêndio em vegetação às margens com fumaça cobrindo a pista; tráfego interrompido.",
    ),
    Template(
        _C.ROAD_BLOCKAGE,
        _S.HIGH,
        "Bloqueio total por acidente grave à frente; sem previsão de liberação.",
    ),
]
TEMPLATES_BY_SEVERITY = {
    severity: [t for t in TEMPLATES if t.severity is severity] for severity in Severity
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


def random_incident_fields(rng: random.Random, severity: Severity | None = None) -> dict[str, Any]:
    """One realistic incident report: a template with coherent severity, a real stretch
    of highway, and sometimes a WhatsApp message. Severity follows the seed's mix when
    not given (~15% high, ~45% medium, ~40% low)."""
    if severity is None:
        severity = rng.choices(list(SEVERITY_COUNTS), weights=list(SEVERITY_COUNTS.values()))[0]
    template = rng.choice(TEMPLATES_BY_SEVERITY[severity])
    stretch = rng.choice(STRETCHES)
    km = Decimal(rng.randint(stretch.km_min * 10, stretch.km_max * 10)) / 10
    truck_code = f"TRK-{rng.randint(1, 5000):04d}"
    source = IncidentSource.WHATSAPP if rng.random() < WHATSAPP_RATIO else IncidentSource.API
    return {
        "description": template.description,
        "category": template.category,
        "severity": severity,
        "truck_code": truck_code,
        "driver_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        "highway": stretch.highway,
        "km": km,
        "location_note": rng.choice(stretch.places),
        "source": source,
        "raw_message": (
            _whatsapp_message(rng, truck_code, f"{stretch.highway} km {km}", template.description)
            if source is IncidentSource.WHATSAPP
            else None
        ),
    }


def build_demo_incidents(
    rng: random.Random,
    now: datetime,
    analysts: list[Analyst],
) -> tuple[list[Incident], list[IncidentEvent]]:
    """The 120-incident demo set, with status history coherent with the timestamps."""
    severities = [sev for sev, count in SEVERITY_COUNTS.items() for _ in range(count)]
    rng.shuffle(severities)

    incidents: list[Incident] = []
    for severity in severities:
        created_at = now - timedelta(seconds=rng.uniform(0, WINDOW.total_seconds()))
        incidents.append(
            Incident(
                id=uuid.uuid4(),
                **random_incident_fields(rng, severity),
                status=IncidentStatus.OPEN,
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


def ensure_analysts(db: Session) -> list[Analyst]:
    """Create the demo analysts only if missing; existing ones keep their ids."""
    existing = {
        a.username: a
        for a in db.scalars(select(Analyst).where(Analyst.username.in_([u for _, u in ANALYSTS])))
    }
    analysts = []
    for name, username in ANALYSTS:
        analyst = existing.get(username)
        if analyst is None:
            analyst = Analyst(
                id=uuid.uuid4(),
                name=name,
                username=username,
                password_hash=hash_password(DEFAULT_PASSWORD),
            )
            db.add(analyst)
        analysts.append(analyst)
    db.flush()
    return analysts


def add_demo_incidents(db: Session, analysts: list[Analyst], now: datetime) -> int:
    incidents, events = build_demo_incidents(random.Random(42), now, analysts)
    db.add_all(incidents)
    db.flush()
    db.add_all(events)
    db.flush()
    return len(incidents)


def seed(db: Session) -> None:
    """Local development only: wipes incidents and their history (see module docstring)."""
    # Both tables in one TRUNCATE satisfies the RESTRICT foreign key between them.
    db.execute(text("TRUNCATE incident_events, incidents"))
    add_demo_incidents(db, ensure_analysts(db), datetime.now(UTC))


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
