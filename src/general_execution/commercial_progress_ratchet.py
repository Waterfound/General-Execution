"""WRM Commercial Progress Ratchet.

Mission-local frontier selection for WRM-001. This module does not execute work,
create authority, contact customers, publish, spend, or activate runtimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommercialRatchetError(ValueError):
    pass


class FrontierKind(str, Enum):
    BUYER_PROBLEM = "BUYER_PROBLEM_EVIDENCE"
    COMPETITIVE_DIFFERENTIATION = "COMPETITIVE_DIFFERENTIATION"
    NARROW_PRODUCT_PROOF = "NARROW_PRODUCT_PROOF"
    EXTERNAL_DEMAND = "EXTERNAL_DEMAND_WILLINGNESS_TO_TRY_WTP"
    FIRST_REVENUE = "FIRST_REVENUE"
    REPEATABILITY = "REPEATABILITY_SUSTAINABLE_ECONOMICS"
    INTERNAL_SUPPORT = "INTERNAL_SUPPORT"


class RatchetDisposition(str, Enum):
    SELECTED = "SELECTED"
    CONDITION_WAIT = "CONDITION_WAIT"
    HUMAN_GATE = "HUMAN_GATE"
    CLOSED = "CLOSED"


_DIRECT_KINDS = {
    FrontierKind.BUYER_PROBLEM,
    FrontierKind.COMPETITIVE_DIFFERENTIATION,
    FrontierKind.NARROW_PRODUCT_PROOF,
    FrontierKind.EXTERNAL_DEMAND,
    FrontierKind.FIRST_REVENUE,
    FrontierKind.REPEATABILITY,
}

_STAGE_RANK = {
    FrontierKind.BUYER_PROBLEM: 1,
    FrontierKind.COMPETITIVE_DIFFERENTIATION: 2,
    FrontierKind.NARROW_PRODUCT_PROOF: 3,
    FrontierKind.EXTERNAL_DEMAND: 4,
    FrontierKind.FIRST_REVENUE: 5,
    FrontierKind.REPEATABILITY: 6,
    FrontierKind.INTERNAL_SUPPORT: 0,
}


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CommercialRatchetError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class CommercialFrontier:
    frontier_id: str
    kind: FrontierKind
    expected_information_gain: int
    prerequisite_satisfied: bool = True
    admissible: bool = True
    human_gate: bool = False
    closed: bool = False
    named_commercial_predicate: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.frontier_id, "frontier_id")
        if not isinstance(self.kind, FrontierKind):
            raise CommercialRatchetError("kind must be a FrontierKind")
        if (
            isinstance(self.expected_information_gain, bool)
            or not isinstance(self.expected_information_gain, int)
            or not 0 <= self.expected_information_gain <= 100
        ):
            raise CommercialRatchetError(
                "expected_information_gain must be an integer from 0 to 100"
            )
        for field in ("prerequisite_satisfied", "admissible", "human_gate", "closed"):
            if not isinstance(getattr(self, field), bool):
                raise CommercialRatchetError(f"{field} must be boolean")
        if self.closed and self.human_gate:
            raise CommercialRatchetError("closed frontier cannot also be a human gate")
        if self.named_commercial_predicate is not None:
            _nonempty(self.named_commercial_predicate, "named_commercial_predicate")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise CommercialRatchetError("evidence_refs must be unique")
        for ref in self.evidence_refs:
            _nonempty(ref, "evidence_refs")


@dataclass(frozen=True, slots=True)
class CommercialRatchetDecision:
    disposition: RatchetDisposition
    selected_frontier_id: str | None
    selected_kind: FrontierKind | None
    classification: str
    reasons: tuple[str, ...]
    rejected_frontiers: tuple[str, ...]
    authority_created: bool = False
    execution_triggered: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, RatchetDisposition):
            raise CommercialRatchetError("disposition must be a RatchetDisposition")
        if self.selected_kind is not None and not isinstance(self.selected_kind, FrontierKind):
            raise CommercialRatchetError("selected_kind must be a FrontierKind")
        if self.authority_created or self.execution_triggered:
            raise CommercialRatchetError(
                "Commercial Progress Ratchet cannot create authority or execute work"
            )
        if self.disposition is RatchetDisposition.SELECTED:
            if self.selected_frontier_id is None or self.selected_kind is None:
                raise CommercialRatchetError("selected decision must bind a frontier")
        elif self.selected_frontier_id is not None or self.selected_kind is not None:
            raise CommercialRatchetError("non-selected decision cannot bind a frontier")


def _sort_key(frontier: CommercialFrontier) -> tuple[int, int, str]:
    # Information gain is primary. Later commercial stage breaks ties only after
    # prerequisites and admissibility have already been proven.
    return (
        frontier.expected_information_gain,
        _STAGE_RANK[frontier.kind],
        frontier.frontier_id,
    )


def select_commercial_frontier(
    frontiers: tuple[CommercialFrontier, ...],
    *,
    technical_capability_proven: bool,
) -> CommercialRatchetDecision:
    """Select the next WRM frontier without letting support work eat the mission.

    Direct commercial work has absolute precedence over internal support whenever
    at least one direct frontier is currently admissible. Internal support after
    capability proof requires a named missing commercial predicate.
    """
    if not isinstance(technical_capability_proven, bool):
        raise CommercialRatchetError("technical_capability_proven must be boolean")

    ids = [frontier.frontier_id for frontier in frontiers]
    if len(ids) != len(set(ids)):
        raise CommercialRatchetError("frontier_id values must be unique")

    direct: list[CommercialFrontier] = []
    support: list[CommercialFrontier] = []
    waits: list[str] = []
    gates: list[str] = []
    rejected: list[str] = []
    closed_count = 0

    for frontier in frontiers:
        if frontier.closed:
            closed_count += 1
            rejected.append(f"{frontier.frontier_id}:closed")
            continue
        if frontier.human_gate:
            gates.append(frontier.frontier_id)
            rejected.append(f"{frontier.frontier_id}:human_gate")
            continue
        if not frontier.prerequisite_satisfied:
            waits.append(frontier.frontier_id)
            rejected.append(f"{frontier.frontier_id}:prerequisite_unsatisfied")
            continue
        if not frontier.admissible:
            waits.append(frontier.frontier_id)
            rejected.append(f"{frontier.frontier_id}:not_admissible")
            continue

        if frontier.kind in _DIRECT_KINDS:
            direct.append(frontier)
            continue

        if frontier.kind is FrontierKind.INTERNAL_SUPPORT:
            if technical_capability_proven and frontier.named_commercial_predicate is None:
                rejected.append(
                    f"{frontier.frontier_id}:support_without_named_commercial_predicate"
                )
                continue
            support.append(frontier)
            continue

        raise CommercialRatchetError(f"unsupported frontier kind: {frontier.kind}")

    pool: list[CommercialFrontier]
    classification: str
    if direct:
        pool = direct
        classification = "DIRECT_COMMERCIAL"
    elif support:
        pool = support
        classification = "SUPPORT_ONLY"
    else:
        if gates and not waits:
            return CommercialRatchetDecision(
                disposition=RatchetDisposition.HUMAN_GATE,
                selected_frontier_id=None,
                selected_kind=None,
                classification="NO_MACHINE_ADMISSIBLE_FRONTIER",
                reasons=("only_current_successors_require_human_authority",),
                rejected_frontiers=tuple(sorted(rejected)),
            )
        if waits:
            return CommercialRatchetDecision(
                disposition=RatchetDisposition.CONDITION_WAIT,
                selected_frontier_id=None,
                selected_kind=None,
                classification="NO_CURRENTLY_ADMISSIBLE_FRONTIER",
                reasons=("current_successors_wait_on_prerequisites_or_conditions",),
                rejected_frontiers=tuple(sorted(rejected)),
            )
        return CommercialRatchetDecision(
            disposition=RatchetDisposition.CLOSED,
            selected_frontier_id=None,
            selected_kind=None,
            classification="NO_OPEN_FRONTIER",
            reasons=(
                (
                    "all_frontiers_closed_or_rejected_without_current_successor"
                    if frontiers
                    else "no_frontiers_supplied"
                ),
            ),
            rejected_frontiers=tuple(sorted(rejected)),
        )

    selected = max(pool, key=_sort_key)
    reasons = [
        "direct_commercial_precedence" if classification == "DIRECT_COMMERCIAL" else "support_only_no_direct_commercial_frontier",
        f"expected_information_gain:{selected.expected_information_gain}",
    ]
    if selected.kind is FrontierKind.INTERNAL_SUPPORT:
        if selected.named_commercial_predicate is not None:
            reasons.append(
                f"named_commercial_predicate:{selected.named_commercial_predicate}"
            )

    return CommercialRatchetDecision(
        disposition=RatchetDisposition.SELECTED,
        selected_frontier_id=selected.frontier_id,
        selected_kind=selected.kind,
        classification=classification,
        reasons=tuple(reasons),
        rejected_frontiers=tuple(sorted(rejected)),
    )
