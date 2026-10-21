"""Demo data: analysts and realistic incidents, reused by the CLI and by /demo.

CLI (local development only): uv run python -m app.seed

The CLI WIPES incidents, incident_events and WhatsApp conversations with TRUNCATE, then
recreates the incidents with timestamps relative to now (last 6 hours). This deletes audit
history on purpose and must never run against a shared or production database.
Analysts are kept with the same ids (created only if missing), so tokens issued
before the seed keep working.

The API never deletes history: POST /demo/reset soft-deletes instead
(see app/services/demo.py).
"""

import random
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.domain.sla import ESCALATION_MINUTES, SLA_MINUTES
from app.models import (
    Analyst,
    CargoType,
    ClientTier,
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentSource,
    IncidentStatus,
    Severity,
    Truck,
)
from app.services.fleet import snapshot_of

TOTAL_INCIDENTS = 120
SEVERITY_COUNTS = {Severity.HIGH: 18, Severity.MEDIUM: 54, Severity.LOW: 48}
INVESTIGATING_COUNT = 20
CLOSED_COUNT = 12
INCONCLUSIVE_COUNT = 3
WINDOW = timedelta(hours=6)
# High-severity incidents by planned fate (the rest of each status goes to medium/low).
HIGH_PLAN = {"open_breached": 3, "investigating": 9, "closed": 4, "inconclusive": 1}
OPEN_BREACHED_OTHERS = 4  # medium/low open incidents already past their SLA
FRESH_MAX_SLA_SHARE = 0.8  # open within the SLA: up to 80% of it elapsed
REACTION_MINUTES = (1, 12)  # time to be assumed (drives the MTTA)
# Accidents with victims always top the queue, so the demo keeps only a few active ones:
# one nobody took yet (escalated) and two being handled. None of the others has victims,
# so the rest of the queue shows the business-impact ranking.
VICTIMS_PLAN = {"open_breached": 1, "investigating": 2}
WHATSAPP_RATIO = 0.3
# WhatsApp reports where the driver did not say where they are.
WHATSAPP_WITHOUT_LOCATION_COUNT = 5
DEFAULT_PASSWORD = "logos123"

ANALYSTS = [("Ana Souza", "ana"), ("Bruno Lima", "bruno")]

# Demo fleet. Every client name is FICTITIOUS (invented for the demo, not real companies).
FLEET_CLIENTS: list[tuple[str, ClientTier, CargoType]] = [
    ("Laticínios Vaca Estrela", ClientTier.STRATEGIC, CargoType.PERISHABLE),
    ("Combustíveis Arara-Azul", ClientTier.STRATEGIC, CargoType.HAZARDOUS),
    ("Farmacêutica Lua Cheia", ClientTier.STRATEGIC, CargoType.HIGH_VALUE),
    ("Química Pinguim Azul", ClientTier.PRIORITY, CargoType.HAZARDOUS),
    ("Frigorífico Boi Celeste", ClientTier.PRIORITY, CargoType.PERISHABLE),
    ("Eletrônicos Coruja Prateada", ClientTier.PRIORITY, CargoType.HIGH_VALUE),
    ("Hortifruti Arco-Íris do Cerrado", ClientTier.STANDARD, CargoType.PERISHABLE),
    ("Grãos Siriema Dourada", ClientTier.STANDARD, CargoType.GENERAL),
    ("Papelaria Capivara Sonhadora", ClientTier.STANDARD, CargoType.GENERAL),
    ("Móveis Jabuti Paciente", ClientTier.STANDARD, CargoType.GENERAL),
]
FLEET_SIZE = 150  # enough for every active demo incident to have its own truck
FLEET_FIRST_CODE = 1001  # TRK-1001 ... TRK-1150
EMPTY_TRIP_EVERY = 8  # every 8th truck is returning empty
UNKNOWN_TRUCK_RATIO = 0.05  # some reports name trucks missing from the fleet


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


def demo_fleet() -> list[Truck]:
    """40 trucks spread over the fictitious clients, each with its client's usual cargo."""
    trucks = []
    for index in range(FLEET_SIZE):
        client, tier, cargo = FLEET_CLIENTS[index % len(FLEET_CLIENTS)]
        if index % EMPTY_TRIP_EVERY == EMPTY_TRIP_EVERY - 1:
            cargo = CargoType.EMPTY
        trucks.append(
            Truck(
                code=f"TRK-{FLEET_FIRST_CODE + index}",
                cargo_type=cargo,
                client_name=client,
                client_tier=tier,
            )
        )
    return trucks


def ensure_fleet(db: Session) -> dict[str, Truck]:
    """Create or refresh the demo fleet (same codes every time)."""
    fleet = {truck.code: db.merge(truck) for truck in demo_fleet()}
    db.flush()
    return fleet


def random_incident_fields(
    rng: random.Random,
    severity: Severity | None = None,
    truck_codes: list[str] | None = None,
    victims: bool | None = None,
    busy: Collection[str] = (),
) -> dict[str, Any]:
    """One realistic incident report: a template with coherent severity, a real stretch
    of highway, and sometimes a WhatsApp message. Severity follows the seed's mix when
    not given (~15% high, ~45% medium, ~40% low). With `truck_codes`, the truck comes
    from the fleet, except a few unknown ones. `victims` forces (True) or excludes (False)
    accidents with victims; None leaves it to chance. Trucks in `busy` are never picked."""
    if severity is None:
        severity = rng.choices(list(SEVERITY_COUNTS), weights=list(SEVERITY_COUNTS.values()))[0]
    templates = TEMPLATES_BY_SEVERITY[severity]
    if victims is not None:
        templates = [
            t
            for t in templates
            if (t.category is IncidentCategory.ACCIDENT_WITH_VICTIMS) == victims
        ]
    template = rng.choice(templates)
    stretch = rng.choice(STRETCHES)
    km = Decimal(rng.randint(stretch.km_min * 10, stretch.km_max * 10)) / 10
    free = [code for code in truck_codes or () if code not in busy]
    if free and rng.random() >= UNKNOWN_TRUCK_RATIO:
        truck_code = rng.choice(free)
    else:
        truck_code = f"TRK-{rng.randint(9000, 9999)}"  # not in the demo fleet
        while truck_code in busy:
            truck_code = f"TRK-{rng.randint(9000, 9999)}"
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


def _assign_statuses(rng: random.Random, severities: list[Severity]) -> list[str]:
    """Plan each incident's fate, keeping the status totals. Most high-severity
    incidents are already being handled; the few left open are the escalated ones."""
    plan: list[str | None] = [None] * len(severities)
    highs = [i for i, s in enumerate(severities) if s is Severity.HIGH]
    others = [i for i, s in enumerate(severities) if s is not Severity.HIGH]
    rng.shuffle(highs)
    rng.shuffle(others)

    for kind, count in HIGH_PLAN.items():
        for _ in range(count):
            plan[highs.pop()] = kind
    remaining = {
        "investigating": INVESTIGATING_COUNT - HIGH_PLAN["investigating"],
        "closed": CLOSED_COUNT - HIGH_PLAN["closed"],
        "inconclusive": INCONCLUSIVE_COUNT - HIGH_PLAN["inconclusive"],
        "open_breached": OPEN_BREACHED_OTHERS,
    }
    for kind, count in remaining.items():
        for _ in range(count):
            plan[others.pop()] = kind
    return [kind or "open_fresh" for kind in plan]


def _minutes(rng: random.Random, low: float, high: float) -> timedelta:
    return timedelta(minutes=rng.uniform(low, high))


def build_demo_incidents(
    rng: random.Random,
    now: datetime,
    analysts: list[Analyst],
    fleet: dict[str, Truck] | None = None,
) -> tuple[list[Incident], list[IncidentEvent]]:
    """The 120-incident demo set, with status history coherent with the timestamps.

    Realistic on purpose, so the signal is not lost in red: almost every open incident
    is still within its SLA (app/domain/sla.py); only a handful are past it, including
    the escalated high-severity ones. Assumed incidents took 1 to 12 minutes to react.
    Each truck has at most one active incident; resolved ones may repeat a truck.
    """
    severities = [sev for sev, count in SEVERITY_COUNTS.items() for _ in range(count)]
    rng.shuffle(severities)
    plan = _assign_statuses(rng, severities)
    with_victims: set[int] = set()
    for kind, count in VICTIMS_PLAN.items():
        slots = [
            i
            for i, (sev, k) in enumerate(zip(severities, plan, strict=True))
            if sev is Severity.HIGH and k == kind
        ]
        with_victims.update(rng.sample(slots, count))

    incidents: list[Incident] = []
    events: list[IncidentEvent] = []
    busy: set[str] = set()  # trucks that already have an active incident
    for index, (severity, kind) in enumerate(zip(severities, plan, strict=True)):
        active = kind.startswith("open") or kind == "investigating"
        sla = SLA_MINUTES[severity]
        if kind == "open_fresh":  # within the SLA, some already amber (near it)
            created_at = now - _minutes(rng, 0.2, sla * FRESH_MAX_SLA_SHARE)
        elif kind == "open_breached" and severity is Severity.HIGH:  # escalated: "Sem dono"
            created_at = now - _minutes(rng, ESCALATION_MINUTES + 1, ESCALATION_MINUTES + 20)
        elif kind == "open_breached":
            created_at = now - _minutes(rng, sla + 2, sla + 30)
        elif kind == "investigating":
            created_at = now - _minutes(rng, 20, 150)
        else:  # closed / inconclusive, spread over the window
            created_at = now - _minutes(rng, 45, WINDOW.total_seconds() / 60)

        fields = random_incident_fields(
            rng,
            severity,
            list(fleet) if fleet else None,
            victims=index in with_victims,
            busy=busy if active else (),
        )
        if active:
            busy.add(fields["truck_code"])
        incident = Incident(
            id=uuid.uuid4(),
            **fields,
            # Copy of the fleet data at creation time (same rule as ingestion).
            **snapshot_of((fleet or {}).get(fields["truck_code"])).as_fields(),
            status=IncidentStatus.OPEN,
            version=1,
            created_at=created_at,
            updated_at=created_at,
        )
        incidents.append(incident)
        events.append(
            IncidentEvent(
                incident_id=incident.id,
                event_type=IncidentEventType.CREATED,
                from_status=None,
                to_status=IncidentStatus.OPEN,
                created_at=created_at,
            )
        )
        if kind.startswith("open"):
            continue

        analyst = rng.choice(analysts)
        acknowledged_at = created_at + _minutes(rng, *REACTION_MINUTES)
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
        if kind == "investigating":
            continue

        final_status = IncidentStatus.CLOSED if kind == "closed" else IncidentStatus.INCONCLUSIVE
        resolved_at = min(acknowledged_at + _minutes(rng, 10, 90), now - timedelta(minutes=1))
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

    whatsapp = [i for i in incidents if i.source is IncidentSource.WHATSAPP]
    for incident in rng.sample(whatsapp, WHATSAPP_WITHOUT_LOCATION_COUNT):
        incident.highway = None
        incident.km = None
        incident.location_note = None
        incident.raw_message = _whatsapp_message(
            rng, incident.truck_code, None, incident.description
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
    incidents, events = build_demo_incidents(random.Random(42), now, analysts, ensure_fleet(db))
    db.add_all(incidents)
    db.flush()
    db.add_all(events)
    db.flush()
    return len(incidents)


def seed(db: Session) -> None:
    """Local development only: wipes incidents and their history (see module docstring)."""
    # One TRUNCATE for every table that references incidents (RESTRICT foreign keys).
    db.execute(text("TRUNCATE conversation_messages, conversations, incident_events, incidents"))
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
