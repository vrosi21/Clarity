"""TaskFSM tests — transition validation + safety property."""
from __future__ import annotations

import pytest

from app.core.fsm import InvalidTransitionError, TaskFSM
from app.models.enums import StageType
from app.models.stage import Stage


def _stage(id: int, order: int, type_: StageType, name: str = "s") -> Stage:
    return Stage(id=id, project_id=1, name=name, order=order, type=type_, color=None)


@pytest.fixture
def stages() -> list[Stage]:
    return [
        _stage(1, 0, StageType.START, "Backlog"),
        _stage(2, 1, StageType.NORMAL, "Todo"),
        _stage(3, 2, StageType.NORMAL, "InProgress"),
        _stage(4, 3, StageType.NORMAL, "Review"),
        _stage(5, 4, StageType.FINAL, "Done"),
    ]


def test_constructor_requires_start(stages):
    with pytest.raises(ValueError, match="START"):
        TaskFSM([_stage(1, 0, StageType.NORMAL), _stage(2, 1, StageType.FINAL)])


def test_constructor_requires_final(stages):
    with pytest.raises(ValueError, match="FINAL"):
        TaskFSM([_stage(1, 0, StageType.START), _stage(2, 1, StageType.NORMAL)])


def test_forward_one_step_allowed(stages):
    fsm = TaskFSM(stages)
    assert fsm.evaluate(1, 2).allowed
    assert fsm.evaluate(2, 3).allowed


def test_jump_two_forward_rejected(stages):
    fsm = TaskFSM(stages)
    assert not fsm.evaluate(1, 3).allowed


def test_normal_to_final_allowed(stages):
    fsm = TaskFSM(stages)
    assert fsm.evaluate(4, 5).allowed
    assert fsm.evaluate(2, 5).allowed  # any NORMAL -> FINAL


def test_start_to_final_blocked(stages):
    """The headline safety property: START → FINAL must be rejected."""
    fsm = TaskFSM(stages)
    decision = fsm.evaluate(1, 5)
    assert not decision.allowed
    assert "Safety" in (decision.reason or "")


def test_safety_property_holds_for_valid_history(stages):
    fsm = TaskFSM(stages)
    assert fsm.check_safety_property([1, 2, 3, 4, 5]) is True


def test_safety_property_violated_when_no_normal_visited(stages):
    fsm = TaskFSM(stages)
    assert fsm.check_safety_property([1, 5]) is False


def test_validate_raises_for_invalid(stages):
    fsm = TaskFSM(stages)
    with pytest.raises(InvalidTransitionError):
        fsm.validate(1, 5)


def test_validate_passes_for_valid(stages):
    fsm = TaskFSM(stages)
    fsm.validate(1, 2)  # should not raise


def test_normal_backwards_allowed(stages):
    fsm = TaskFSM(stages)
    # Review -> Todo (send back during review)
    assert fsm.evaluate(4, 2).allowed


def test_valid_next_stages(stages):
    fsm = TaskFSM(stages)
    next_stages = fsm.valid_next_stages(2)  # from Todo
    next_ids = {s.id for s in next_stages}
    # Forward by 1 (3=InProgress) and any NORMAL→FINAL (5=Done) and backwards within NORMAL band (none lower than 2 is normal)
    assert 3 in next_ids
    assert 5 in next_ids
