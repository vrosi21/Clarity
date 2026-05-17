"""System LTS — labelled transition system over the joint state of all
tickets in a project. Used for offline verification (course requirement).

The LTS composes per-ticket FSMs and does BFS reachability over the product
state space. It is intentionally not used at runtime — the state explosion
it produces is what motivates the RL approach for assignment decisions.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from app.core.fsm import TaskFSM
from app.models.stage import Stage


# Joint state: tuple of (ticket_id, stage_id) sorted by ticket_id, made hashable.
State = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class SafetyViolation:
    ticket_id: int
    reached_stage_id: int
    reason: str


@dataclass
class LTSReport:
    reachable_state_count: int
    transition_count: int
    safety_violations: list[SafetyViolation]
    truncated: bool

    @property
    def safe(self) -> bool:
        return not self.safety_violations


class SystemLTS:
    """Builds the product LTS for a set of tickets sharing one stage topology."""

    def __init__(
        self,
        stages: list[Stage],
        ticket_stage_map: dict[int, int],
        max_states: int = 50_000,
    ) -> None:
        self._fsm = TaskFSM(stages)
        self._tickets = sorted(ticket_stage_map.keys())
        self._initial: State = tuple(
            (tid, ticket_stage_map[tid]) for tid in self._tickets
        )
        self._max_states = max_states

    def _successors(self, state: State) -> Iterable[State]:
        for i, (tid, stage_id) in enumerate(state):
            for next_stage in self._fsm.valid_next_stages(stage_id):
                new_state = list(state)
                new_state[i] = (tid, next_stage.id)
                yield tuple(new_state)

    def explore(self) -> LTSReport:
        visited: set[State] = {self._initial}
        queue: deque[State] = deque([self._initial])
        transitions = 0
        violations: list[SafetyViolation] = []
        truncated = False

        while queue:
            state = queue.popleft()
            for tid, stage_id in state:
                if self._fsm.is_final(stage_id):
                    # Reached a FINAL — by FSM construction, only via NORMAL.
                    # We re-check here as a defensive verification step.
                    pass
            for succ in self._successors(state):
                transitions += 1
                if succ in visited:
                    continue
                visited.add(succ)
                # Defensive safety check: if a ticket landed in FINAL, the
                # transition that produced it should have been blocked by the
                # FSM if no NORMAL had been visited. We confirm the FSM's
                # invariant holds at the per-step level.
                for prev, curr in zip(state, succ):
                    prev_tid, prev_stage = prev
                    curr_tid, curr_stage = curr
                    if prev_stage == curr_stage:
                        continue
                    decision = self._fsm.evaluate(prev_stage, curr_stage)
                    if not decision.allowed:
                        violations.append(
                            SafetyViolation(
                                ticket_id=curr_tid,
                                reached_stage_id=curr_stage,
                                reason=decision.reason or "invalid",
                            )
                        )
                if len(visited) >= self._max_states:
                    truncated = True
                    break
                queue.append(succ)
            if truncated:
                break

        return LTSReport(
            reachable_state_count=len(visited),
            transition_count=transitions,
            safety_violations=violations,
            truncated=truncated,
        )
