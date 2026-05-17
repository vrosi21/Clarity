"""Task FSM — formal model for ticket stage transitions.

The FSM is anchored on the project's `Stage` rows. Each `Stage.type`
(START / NORMAL / FINAL) determines the role of the state. Transitions are
validated against a structural rule and a per-project topology rule.

Safety property (course requirement):
    A ticket can never reach a FINAL stage without first having traversed
    a NORMAL stage. The FSM rejects any transition that would violate this.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import StageType
from app.models.stage import Stage


class InvalidTransitionError(ValueError):
    """Raised when a transition is rejected by the FSM."""


@dataclass(frozen=True)
class TransitionDecision:
    allowed: bool
    reason: str | None = None


class TaskFSM:
    """Validates ticket stage transitions for a single project.

    The project's stages, ordered by `Stage.order`, define the FSM topology.
    Allowed transitions are: stay-or-advance one step, or jump to any FINAL
    stage *only if* a NORMAL stage has been visited. Backwards moves are
    permitted within the NORMAL band (e.g. send-back from review).
    """

    def __init__(self, stages: list[Stage]) -> None:
        if not stages:
            raise ValueError("FSM requires at least one stage")
        self._stages = sorted(stages, key=lambda s: s.order)
        self._by_id = {s.id: s for s in self._stages}
        starts = [s for s in self._stages if s.type == StageType.START]
        finals = [s for s in self._stages if s.type == StageType.FINAL]
        if not starts:
            raise ValueError("FSM requires exactly one START stage")
        if len(starts) > 1:
            raise ValueError("FSM allows at most one START stage")
        if not finals:
            raise ValueError("FSM requires at least one FINAL stage")
        self._start = starts[0]
        self._finals = {s.id for s in finals}
        self._normals = {
            s.id for s in self._stages if s.type == StageType.NORMAL
        }

    @property
    def start_stage(self) -> Stage:
        return self._start

    def is_final(self, stage_id: int) -> bool:
        return stage_id in self._finals

    def is_normal(self, stage_id: int) -> bool:
        return stage_id in self._normals

    def evaluate(
        self,
        from_stage_id: int,
        to_stage_id: int,
        history: list[int] | None = None,
    ) -> TransitionDecision:
        """Pure check — does not raise. Returns a TransitionDecision."""
        if from_stage_id not in self._by_id:
            return TransitionDecision(False, "Unknown source stage")
        if to_stage_id not in self._by_id:
            return TransitionDecision(False, "Unknown target stage")
        if from_stage_id == to_stage_id:
            return TransitionDecision(False, "Already in target stage")

        # Safety property: cannot enter FINAL without having visited a NORMAL.
        if self.is_final(to_stage_id):
            visited_normal = any(self.is_normal(s) for s in (history or []))
            if not visited_normal and not self.is_normal(from_stage_id):
                return TransitionDecision(
                    False,
                    "Safety violation: cannot enter FINAL without passing through a NORMAL stage",
                )

        # Topology: forward by 1, or backwards within the NORMAL band, or
        # any-NORMAL → any-FINAL.
        from_idx = self._stages.index(self._by_id[from_stage_id])
        to_idx = self._stages.index(self._by_id[to_stage_id])
        if to_idx - from_idx == 1:
            return TransitionDecision(True)
        if self.is_final(to_stage_id) and self.is_normal(from_stage_id):
            return TransitionDecision(True)
        if (
            self.is_normal(from_stage_id)
            and self.is_normal(to_stage_id)
            and to_idx < from_idx
        ):
            return TransitionDecision(True)
        return TransitionDecision(False, "Transition not allowed by topology")

    def validate(
        self,
        from_stage_id: int,
        to_stage_id: int,
        history: list[int] | None = None,
    ) -> None:
        """Raises InvalidTransitionError if not allowed."""
        decision = self.evaluate(from_stage_id, to_stage_id, history)
        if not decision.allowed:
            raise InvalidTransitionError(decision.reason or "Invalid transition")

    def valid_next_stages(
        self, from_stage_id: int, history: list[int] | None = None
    ) -> list[Stage]:
        return [
            s
            for s in self._stages
            if self.evaluate(from_stage_id, s.id, history).allowed
        ]

    def check_safety_property(self, history: list[int]) -> bool:
        """Returns True iff the history satisfies the FINAL-via-NORMAL invariant."""
        seen_normal = False
        for stage_id in history:
            if self.is_normal(stage_id):
                seen_normal = True
            if self.is_final(stage_id) and not seen_normal:
                return False
        return True
