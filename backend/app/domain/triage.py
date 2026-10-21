"""WhatsApp triage bot: a guided conversation that turns a driver's report into an
incident (ADR 0005). Pure functions, no database: the service stores the step and the
partial data between messages.

Severity rules (the bot measures the problem; cargo and client come from the fleet
through the priority score, so the bot never asks about them):

| Problem             | Someone injured | Truck can go on | Category              | Severity |
|---------------------|-----------------|-----------------|-----------------------|----------|
| any                 | yes             | any             | accident_with_victims | high     |
| 1 Acidente          | no              | no              | vehicle_accident      | high     |
| 1 Acidente          | no              | yes             | vehicle_accident      | medium   |
| 2, 3 or 4           | no              | no              | (problem's category)  | medium   |
| 2, 3 or 4           | no              | yes             | (problem's category)  | low      |
"""

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.models.enums import IncidentCategory, Severity

C = IncidentCategory


class Step(StrEnum):
    TRUCK = "truck"
    PROBLEM = "problem"
    INJURED = "injured"
    LOCATION = "location"
    CAN_CONTINUE = "can_continue"
    DESCRIPTION = "description"


TRUCK_CODE = re.compile(r"^TRK[\s-]?(\d{4})$")
CANCEL = "cancelar"
DONT_KNOW = ("nao sei", "não sei", "sei nao", "sei não")
SKIP = "pular"

# Option label shown to the driver -> category.
PROBLEMS: dict[str, tuple[str, IncidentCategory]] = {
    "1": ("Acidente", C.VEHICLE_ACCIDENT),
    "2": ("Problema mecânico", C.MECHANICAL_FAILURE),
    "3": ("Clima", C.ADVERSE_WEATHER),
    "4": ("Bloqueio de pista", C.ROAD_BLOCKAGE),
}
_PROBLEM_WORDS = {
    "acidente": "1",
    "mecanico": "2",
    "problema mecanico": "2",
    "clima": "3",
    "bloqueio": "4",
    "bloqueio de pista": "4",
}
YES = ("sim", "s")
NO = ("nao", "n")

GREETING = "Olá! Aqui é a central de incidentes da Logos. Vou registrar sua ocorrência."
QUESTIONS: dict[Step, str] = {
    Step.TRUCK: "Qual é o código do caminhão? (ex.: TRK-1001)",
    Step.PROBLEM: "O que aconteceu? Responda com o número:\n"
    + "\n".join(f"{key} {label}" for key, (label, _) in PROBLEMS.items()),
    Step.INJURED: "Tem alguém ferido? (sim/não)",
    Step.LOCATION: (
        'Onde você está? Rodovia, km ou uma referência. Se não souber, responda "não sei".'
    ),
    Step.CAN_CONTINUE: "O caminhão consegue seguir viagem? (sim/não)",
    Step.DESCRIPTION: 'Descreva em poucas palavras o que aconteceu (ou responda "pular").',
}
# Quick replies the simulator shows as buttons.
OPTIONS: dict[Step, list[str]] = {
    Step.PROBLEM: [f"{key} {label}" for key, (label, _) in PROBLEMS.items()],
    Step.INJURED: ["Sim", "Não"],
    Step.LOCATION: ["Não sei"],
    Step.CAN_CONTINUE: ["Sim", "Não"],
    Step.DESCRIPTION: ["Pular"],
}
INVALID: dict[Step, str] = {
    Step.TRUCK: "Não reconheci esse código. Ele fica na porta do caminhão, no formato TRK-0000.",
    Step.PROBLEM: "Não entendi. Responda só com o número da opção.",
    Step.INJURED: 'Não entendi. Responda "sim" ou "não".',
    Step.CAN_CONTINUE: 'Não entendi. Responda "sim" ou "não".',
}
CANCELLED = "Tudo bem, cancelei o registro. Se precisar, é só mandar uma nova mensagem."

ORDER = list(Step)


@dataclass
class Turn:
    """The bot's answer to one message."""

    replies: list[str]
    step: Step | None  # None: the conversation ended (completed or cancelled)
    data: dict[str, Any] = field(default_factory=dict)
    completed: bool = False


def normalize(text: str) -> str:
    """Lowercase, no accents, no surrounding punctuation or extra spaces."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().strip(" .!?").split())


def start() -> Turn:
    return Turn(replies=[GREETING, QUESTIONS[Step.TRUCK]], step=Step.TRUCK)


def _yes_no(text: str) -> bool | None:
    answer = normalize(text)
    if answer in YES:
        return True
    if answer in NO:
        return False
    return None


def _parse(step: Step, text: str) -> tuple[bool, Any]:
    """(valid, value) for the answer to `step`."""
    match step:
        case Step.TRUCK:
            found = TRUCK_CODE.match(text.strip().upper())
            return (True, f"TRK-{found.group(1)}") if found else (False, None)
        case Step.PROBLEM:
            answer = normalize(text)
            key = answer if answer in PROBLEMS else _PROBLEM_WORDS.get(answer)
            if key is None and answer[:1] in PROBLEMS and not answer[1:2].isdigit():
                key = answer[:1]  # "1 Acidente" (the button text)
            return (True, key) if key else (False, None)
        case Step.INJURED | Step.CAN_CONTINUE:
            value = _yes_no(text)
            return value is not None, value
        case Step.LOCATION:
            return True, None if normalize(text) in {
                normalize(d) for d in DONT_KNOW
            } else text.strip()
        case Step.DESCRIPTION:
            return True, None if normalize(text) == SKIP else text.strip()


def advance(step: Step, data: dict[str, Any], text: str) -> Turn:
    """Apply the driver's answer to the current step."""
    if normalize(text) == CANCEL:
        return Turn(replies=[CANCELLED], step=None, data=data)

    valid, value = _parse(step, text)
    if not valid:
        options = f"\n{QUESTIONS[step]}" if step is not Step.TRUCK else ""
        return Turn(replies=[INVALID[step] + options], step=step, data=data)

    data = {**data, step.value: value}
    following = ORDER.index(step) + 1
    if following < len(ORDER):
        next_step = ORDER[following]
        return Turn(replies=[QUESTIONS[next_step]], step=next_step, data=data)
    return Turn(replies=[], step=None, data=data, completed=True)


def classify(data: dict[str, Any]) -> tuple[IncidentCategory, Severity]:
    """Category and severity from the answers (table in the module docstring)."""
    if data["injured"]:
        return C.ACCIDENT_WITH_VICTIMS, Severity.HIGH
    category = PROBLEMS[data["problem"]][1]
    stopped = not data["can_continue"]
    if category is C.VEHICLE_ACCIDENT:
        return category, Severity.HIGH if stopped else Severity.MEDIUM
    return category, Severity.MEDIUM if stopped else Severity.LOW


_HIGHWAY = re.compile(r"\b([A-Za-z]{2})[\s-]?(\d{2,3})\b")
_KM = re.compile(r"\bkm\s*(\d{1,4}(?:[.,]\d+)?)", re.IGNORECASE)


def location_fields(text: str | None) -> dict[str, Any]:
    """Highway and km found in the free text; the text itself goes to location_note.
    The ingestion schema salvages anything unusable (it never rejects a location)."""
    if not text:
        return {}
    highway = _HIGHWAY.search(text)
    km = _KM.search(text)
    return {
        "highway": f"{highway.group(1)}-{highway.group(2)}".upper() if highway else None,
        "km": km.group(1).replace(",", ".") if km else None,
        "location_note": text,
    }


def description(data: dict[str, Any]) -> str:
    """The driver's words (or the chosen problem) plus the triage answers."""
    label = PROBLEMS[data["problem"]][0]
    facts = [
        "com feridos" if data["injured"] else "sem feridos",
        "segue viagem" if data["can_continue"] else "caminhão parado",
    ]
    told = data.get("description") or f"{label} relatado pelo motorista"
    return f"{told.rstrip('.')}. Triagem: {label.lower()}, {', '.join(facts)}."
