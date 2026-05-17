"""SystemLTS tests — reachability + safety check."""
from __future__ import annotations

import pytest

from app.core.lts import SystemLTS
from app.models.enums import StageType
from app.models.stage import Stage


def _stage(id: int, order: int, type_: StageType) -> Stage:
    return Stage(id=id, project_id=1, name=f"s{id}", order=order, type=type_, color=None)


@pytest.fixture
def stages() -> list[Stage]:
    return [
        _stage(1, 0, StageType.START),
        _stage(2, 1, StageType.NORMAL),
        _stage(3, 2, StageType.NORMAL),
        _stage(4, 3, StageType.FINAL),
    ]


def test_single_ticket_explores_full_path(stages):
    lts = SystemLTS(stages, ticket_stage_map={100: 1})
    report = lts.explore()
    assert report.reachable_state_count >= 4  # at least one state per stage
    assert report.safe is True
    assert report.truncated is False


def test_two_tickets_state_space_grows(stages):
    lts = SystemLTS(stages, ticket_stage_map={100: 1, 200: 1})
    report = lts.explore()
    # With 2 tickets and 4 stages → bounded but > 4.
    assert report.reachable_state_count > 4
    assert report.safe is True


def test_truncation_triggered_with_low_cap(stages):
    lts = SystemLTS(
        stages, ticket_stage_map={100: 1, 200: 1, 300: 1}, max_states=3
    )
    report = lts.explore()
    assert report.truncated is True


def test_no_violations_in_bfs(stages):
    """The FSM blocks bad transitions, so the LTS should never produce one."""
    lts = SystemLTS(stages, ticket_stage_map={100: 1})
    report = lts.explore()
    assert report.safety_violations == []
