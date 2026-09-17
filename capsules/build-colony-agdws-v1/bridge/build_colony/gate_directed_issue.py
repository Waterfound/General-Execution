from __future__ import annotations

from dataclasses import dataclass

from .ledger import append_event, execution_frontier
from .protocol import RunManifest, sha256_digest
from .state_models import EventType, RunLedger
from .work_selection import (
    WorkSelectionContract,
    WorkSelectionDecision,
    select_gate_directed_work,
)


@dataclass(frozen=True)
class GateDirectedIssueResult:
    ledger: RunLedger
    decision: WorkSelectionDecision
    selection_contract_digest: str
    selection_decision_digest: str


def issue_gate_directed_ready(
    manifest: RunManifest,
    ledger: RunLedger,
    contract: WorkSelectionContract,
) -> GateDirectedIssueResult:
    """Issue only active-gate-relevant ready packages.

    AGDWS is intentionally placed before the existing dispatch planner. The
    existing planner therefore sees only packages that the coordinator has
    issued through this bounded gate-directed path; runner assignment,
    verification, integration, and ledger semantics remain unchanged.
    """
    frontier = execution_frontier(manifest, ledger)
    decision = select_gate_directed_work(frontier.ready, contract)
    contract_digest = sha256_digest(contract)
    decision_digest = sha256_digest(decision)
    package_by_domain = {package.domain_id: package for package in manifest.packages}

    updated = ledger
    for domain_id in decision.eligible_domains:
        package = package_by_domain[domain_id]
        updated = append_event(
            manifest,
            updated,
            package_id=package.package_id,
            role="coordinator",
            event_type=EventType.ISSUE.value,
            payload={
                "active_gate_class": contract.active_gate_class.value,
                "native_progress_unit": contract.native_progress_unit,
                "selection_contract_digest": contract_digest,
                "selection_decision_digest": decision_digest,
            },
        )

    return GateDirectedIssueResult(
        ledger=updated,
        decision=decision,
        selection_contract_digest=contract_digest,
        selection_decision_digest=decision_digest,
    )
