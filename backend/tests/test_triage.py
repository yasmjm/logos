import pytest

from app.domain import triage
from app.domain.triage import Step
from app.models import IncidentCategory, Severity


def _run(*answers: str) -> triage.Turn:
    turn = triage.start()
    for answer in answers:
        assert turn.step is not None
        turn = triage.advance(turn.step, turn.data, answer)
    return turn


def test_start_greets_and_asks_for_the_truck() -> None:
    turn = triage.start()

    assert turn.step is Step.TRUCK
    assert turn.replies[-1] == triage.QUESTIONS[Step.TRUCK]


def test_full_conversation_collects_every_answer() -> None:
    turn = _run("trk 1001", "2", "não", "BR-116 km 230", "Não", "Motor ferveu")

    assert turn.completed and turn.step is None
    assert turn.data == {
        "truck": "TRK-1001",
        "problem": "2",
        "injured": False,
        "location": "BR-116 km 230",
        "can_continue": False,
        "description": "Motor ferveu",
    }


@pytest.mark.parametrize("code", ["TRK-1001", "trk1001", "TRK 1001", " trk-1001 "])
def test_truck_code_is_normalized(code: str) -> None:
    turn = _run(code)

    assert turn.step is Step.PROBLEM
    assert turn.data["truck"] == "TRK-1001"


@pytest.mark.parametrize("code", ["1001", "TRK-10", "TRK-12345", "caminhão azul"])
def test_invalid_truck_code_asks_again_kindly(code: str) -> None:
    turn = _run(code)

    assert turn.step is Step.TRUCK
    assert "TRK-0000" in turn.replies[0]
    assert "truck" not in turn.data


@pytest.mark.parametrize(
    ("answer", "key"), [("1", "1"), ("1 Acidente", "1"), ("mecânico", "2"), ("Bloqueio", "4")]
)
def test_problem_accepts_number_button_or_word(answer: str, key: str) -> None:
    assert _run("TRK-1001", answer).data["problem"] == key


@pytest.mark.parametrize("answer", ["5", "12", "pneu", "talvez"])
def test_invalid_problem_repeats_the_question_with_options(answer: str) -> None:
    turn = _run("TRK-1001", answer)

    assert turn.step is Step.PROBLEM
    assert "4 Bloqueio de pista" in turn.replies[0]


def test_invalid_yes_no_repeats_the_question() -> None:
    turn = _run("TRK-1001", "1", "talvez")

    assert turn.step is Step.INJURED
    assert "sim" in turn.replies[0] and "não" in turn.replies[0]


def test_dont_know_location_and_skip_description_are_accepted() -> None:
    turn = _run("TRK-1001", "3", "nao", "Não sei", "sim", "pular")

    assert turn.completed
    assert turn.data["location"] is None
    assert turn.data["description"] is None


@pytest.mark.parametrize("answers", [("cancelar",), ("TRK-1001", "2", "Cancelar")])
def test_cancel_ends_the_conversation_at_any_step(answers: tuple[str, ...]) -> None:
    turn = _run(*answers)

    assert turn.step is None and not turn.completed
    assert turn.replies == [triage.CANCELLED]


@pytest.mark.parametrize(
    ("problem", "injured", "can_continue", "expected"),
    [
        ("2", True, True, (IncidentCategory.ACCIDENT_WITH_VICTIMS, Severity.HIGH)),
        ("1", True, False, (IncidentCategory.ACCIDENT_WITH_VICTIMS, Severity.HIGH)),
        ("1", False, False, (IncidentCategory.VEHICLE_ACCIDENT, Severity.HIGH)),
        ("1", False, True, (IncidentCategory.VEHICLE_ACCIDENT, Severity.MEDIUM)),
        ("2", False, False, (IncidentCategory.MECHANICAL_FAILURE, Severity.MEDIUM)),
        ("3", False, True, (IncidentCategory.ADVERSE_WEATHER, Severity.LOW)),
        ("4", False, False, (IncidentCategory.ROAD_BLOCKAGE, Severity.MEDIUM)),
        ("4", False, True, (IncidentCategory.ROAD_BLOCKAGE, Severity.LOW)),
    ],
)
def test_severity_table(
    problem: str, injured: bool, can_continue: bool, expected: tuple[IncidentCategory, Severity]
) -> None:
    data = {"problem": problem, "injured": injured, "can_continue": can_continue}

    assert triage.classify(data) == expected


def test_location_fields_extract_highway_and_km() -> None:
    assert triage.location_fields("perto do posto, br 116 km 230,5") == {
        "highway": "BR-116",
        "km": "230.5",
        "location_note": "perto do posto, br 116 km 230,5",
    }
    assert triage.location_fields(None) == {}


def test_description_keeps_the_driver_words_and_the_triage_facts() -> None:
    data = {"problem": "2", "injured": False, "can_continue": False, "description": None}

    assert triage.description(data) == (
        "Problema mecânico relatado pelo motorista. "
        "Triagem: problema mecânico, sem feridos, caminhão parado."
    )
