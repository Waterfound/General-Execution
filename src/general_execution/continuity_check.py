from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping, Sequence
import re

SCHEMA_VERSION = "CONTINUITY_CHECK_V1"

EVIDENCE_PRECEDENCE = (
    "canonical_runtime_provider",
    "canonical_repository",
    "durable_state",
    "build_colony_state",
    "canonical_project_ledger",
    "conversation_context",
)

FRESHNESS_RULES = (
    "No universal elapsed-time threshold may create a stalled verdict.",
    "Use frontier-specific timing contracts, wake conditions, schedules, provider-operation semantics, or bounded recovery semantics.",
    "Old GREEN CI alone is not current execution evidence.",
    "Open PR state alone is not current execution evidence.",
    "Conversation timestamps are auxiliary and never override stronger operational evidence.",
)


class ConversationAssessment(str, Enum):
    ACTIVE_OBSERVED = "CONVERSATION_ACTIVE_OBSERVED"
    INTERRUPTION_SUSPECTED = "CONVERSATION_INTERRUPTION_SUSPECTED"
    STATE_UNKNOWN = "CONVERSATION_STATE_UNKNOWN"


class DevelopmentVerdict(str, Enum):
    DEVELOPMENT_PROGRESSING = "DEVELOPMENT_PROGRESSING"
    CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED = "CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED"
    CHECKPOINTED_RESUMABLE = "CHECKPOINTED_RESUMABLE"
    CONDITION_WAIT = "CONDITION_WAIT"
    SCHEDULED_WAIT = "SCHEDULED_WAIT"
    HUMAN_GATE = "HUMAN_GATE"
    EXTERNAL_EVIDENCE_GATE = "EXTERNAL_EVIDENCE_GATE"
    DONE_TECHNICAL = "DONE_TECHNICAL"
    DONE_CANONICAL = "DONE_CANONICAL"
    DEVELOPMENT_STALLED = "DEVELOPMENT_STALLED"
    FAILED = "FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RecommendedAction(str, Enum):
    NO_ACTION_DONE = "NO_ACTION_DONE"
    NO_ACTION_ACTIVE_EXECUTION = "NO_ACTION_ACTIVE_EXECUTION"
    RESUME_DURABLE_EXECUTION = "RESUME_DURABLE_EXECUTION"
    WAIT_FOR_CONDITION = "WAIT_FOR_CONDITION"
    WAIT_UNTIL_SCHEDULED_CHECKPOINT = "WAIT_UNTIL_SCHEDULED_CHECKPOINT"
    REQUEST_HUMAN_ACTION = "REQUEST_HUMAN_ACTION"
    REQUEST_EXTERNAL_EVIDENCE = "REQUEST_EXTERNAL_EVIDENCE"
    INVESTIGATE_FAILURE = "INVESTIGATE_FAILURE"
    RECONCILE_CANONICAL_STATE = "RECONCILE_CANONICAL_STATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class InfrastructureStatus(str, Enum):
    HEALTHY = "HEALTHY"
    PROVIDER_RUNNER_UNAVAILABLE = "PROVIDER_RUNNER_UNAVAILABLE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    NO_PROVIDER_EVIDENCE = "NO_PROVIDER_EVIDENCE"
    MISMATCHED_EVIDENCE = "MISMATCHED_EVIDENCE"
    UNKNOWN = "UNKNOWN"


class ProviderState(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    QUEUED = "QUEUED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class FailureScope(str, Enum):
    NONE = "NONE"
    PROVIDER = "PROVIDER"
    WORKLOAD = "WORKLOAD"


class GateKind(str, Enum):
    HUMAN = "HUMAN"
    EXTERNAL_EVIDENCE = "EXTERNAL_EVIDENCE"


class LaunchDisposition(str, Enum):
    ADMITTED = "ADMITTED"
    HUMAN_GATE = "HUMAN_GATE"
    REJECTED = "REJECTED"
    FAILED_BEFORE_LAUNCH = "FAILED_BEFORE_LAUNCH"


@dataclass(frozen=True, slots=True)
class WorkstreamCandidate:
    workstream_id: str
    canonical_name: str
    repository: str | None = None
    branch: str | None = None
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.workstream_id.strip() or not self.canonical_name.strip():
            raise ValueError("workstream identity fields must be non-empty")


@dataclass(frozen=True, slots=True)
class WorkstreamResolution:
    query: str
    status: str
    candidate: WorkstreamCandidate | None
    matches: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationEvidence:
    assessment: ConversationAssessment = ConversationAssessment.STATE_UNKNOWN
    last_observed_at: str | None = None


@dataclass(frozen=True, slots=True)
class RepositoryEvidence:
    repository: str
    main_revision: str | None = None
    branch: str | None = None
    branch_head: str | None = None
    latest_related_commit: str | None = None
    latest_related_commit_at: str | None = None
    pull_request_number: int | None = None
    pull_request_state: str | None = None
    pull_request_mergeable: bool | None = None
    pull_request_merged: bool = False
    canonical_contains_workstream: bool = False

    def __post_init__(self) -> None:
        if not self.repository.strip():
            raise ValueError("repository must be non-empty")
        if self.pull_request_number is not None and self.pull_request_number < 1:
            raise ValueError("pull_request_number must be >= 1")


@dataclass(frozen=True, slots=True)
class DurableStateEvidence:
    validated: bool
    workstream_id: str
    bound_repository: str | None = None
    bound_branch: str | None = None
    bound_branch_head: str | None = None
    current_frontier: str | None = None
    completed_frontiers: tuple[str, ...] = ()
    admissible_next: tuple[str, ...] = ()
    active_dispatch: bool = False
    last_progress_at: str | None = None
    wake_condition: str | None = None
    scheduled_checkpoint: str | None = None
    execution_expected: bool = False
    recovery_semantics_exhausted: bool = False
    terminal_verdict: str | None = None
    failed_terminal_reason: str | None = None


@dataclass(frozen=True, slots=True)
class BuildColonyEvidence:
    validated: bool
    workstream_id: str
    bound_repository: str | None = None
    bound_branch: str | None = None
    bound_branch_head: str | None = None
    current_frontier: str | None = None
    completed_frontiers: tuple[str, ...] = ()
    admissible_next: tuple[str, ...] = ()
    terminal_verdict: str | None = None
    last_progress_at: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderEvidence:
    provider: str
    state: ProviderState
    observed_at: str | None = None
    subject_revision: str | None = None
    failure_scope: FailureScope = FailureScope.NONE
    detail: str | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")
        if self.failure_scope is FailureScope.WORKLOAD and self.state is not ProviderState.FAILED:
            raise ValueError("workload failure scope requires FAILED provider state")


@dataclass(frozen=True, slots=True)
class GateEvidence:
    kind: GateKind
    ref: str
    reason: str
    frontier: str
    satisfied: bool = False

    def __post_init__(self) -> None:
        for value in (self.ref, self.reason, self.frontier):
            if not value.strip():
                raise ValueError("gate ref, reason and frontier must be non-empty")


@dataclass(frozen=True, slots=True)
class LaunchAdmissionEvidence:
    validated: bool
    workstream_id: str
    disposition: LaunchDisposition
    receipt_ref: str
    launch_id: str | None = None
    repository: str | None = None
    executor: str | None = None
    dispatch_identity: str | None = None
    first_artifact_ref: str | None = None
    observed_at: str | None = None
    recovery_semantics_exhausted: bool = False
    detail: str | None = None

    def __post_init__(self) -> None:
        if not self.workstream_id.strip() or not self.receipt_ref.strip():
            raise ValueError("launch admission identity must be non-empty")
        if self.disposition is LaunchDisposition.ADMITTED:
            if not self.launch_id or not self.dispatch_identity:
                raise ValueError("ADMITTED launch evidence requires launch/dispatch identity")


@dataclass(frozen=True, slots=True)
class ContinuitySnapshot:
    checked_at: str
    query: str
    candidates: tuple[WorkstreamCandidate, ...]
    conversation: ConversationEvidence = field(default_factory=ConversationEvidence)
    repository: RepositoryEvidence | None = None
    durable: DurableStateEvidence | None = None
    build_colony: BuildColonyEvidence | None = None
    provider: ProviderEvidence | None = None
    launch_admission: LaunchAdmissionEvidence | None = None
    gates: tuple[GateEvidence, ...] = ()
    canonical_integration_required: bool = True


@dataclass(frozen=True, slots=True)
class ContinuityReport:
    schema: str
    workstream: str
    workstream_id: str | None
    checked_at: str
    conversation_assessment: str
    development_verdict: str
    repository: str | None
    main_revision: str | None
    branch: str | None
    branch_head: str | None
    pull_request: Mapping[str, object] | None
    durable_state: Mapping[str, object] | None
    latest_execution_evidence: Mapping[str, object] | None
    blocking_gate: Mapping[str, object] | None
    infrastructure_status: str
    evidence_warnings: tuple[str, ...]
    recommended_action: str
    canonical_state_reconciliation_recommended: bool
    authority_created: bool = False
    execution_triggered: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _norm(text: str) -> str:
    value = text.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def resolve_workstream(query: str, candidates: Sequence[WorkstreamCandidate]) -> WorkstreamResolution:
    q = _norm(query)
    if not q:
        return WorkstreamResolution(query=query, status="NOT_FOUND", candidate=None)
    exact: list[WorkstreamCandidate] = []
    partial: list[WorkstreamCandidate] = []
    for candidate in candidates:
        names = (candidate.canonical_name, candidate.workstream_id, *candidate.aliases)
        normalized = {_norm(name) for name in names}
        if q in normalized:
            exact.append(candidate)
        elif any(q in name or name in q for name in normalized if name):
            partial.append(candidate)
    pool = exact if exact else partial
    unique = {item.workstream_id: item for item in pool}
    if len(unique) == 1:
        candidate = next(iter(unique.values()))
        return WorkstreamResolution(query=query, status="RESOLVED", candidate=candidate, matches=(candidate.workstream_id,))
    if len(unique) > 1:
        return WorkstreamResolution(query=query, status="AMBIGUOUS", candidate=None, matches=tuple(sorted(unique)))
    return WorkstreamResolution(query=query, status="NOT_FOUND", candidate=None)


def _durable_matches_repo(durable: DurableStateEvidence, repo: RepositoryEvidence | None) -> bool:
    if not durable.validated:
        return False
    if repo is None:
        return True
    if durable.bound_repository and durable.bound_repository != repo.repository:
        return False
    if durable.bound_branch and repo.branch and durable.bound_branch != repo.branch:
        return False
    if durable.bound_branch_head and repo.branch_head and durable.bound_branch_head != repo.branch_head:
        return False
    return True


def _build_colony_matches_repo(state: BuildColonyEvidence, repo: RepositoryEvidence | None) -> bool:
    if not state.validated:
        return False
    if repo is None:
        return True
    if state.bound_repository and state.bound_repository != repo.repository:
        return False
    if state.bound_branch and repo.branch and state.bound_branch != repo.branch:
        return False
    if state.bound_branch_head and repo.branch_head and state.bound_branch_head != repo.branch_head:
        return False
    return True


def _provider_matches_repo(provider: ProviderEvidence, repo: RepositoryEvidence | None) -> bool:
    if repo is None or not provider.subject_revision:
        return True
    revisions = {rev for rev in (repo.branch_head, repo.main_revision) if rev}
    return provider.subject_revision in revisions


def _launch_matches_repo(launch: LaunchAdmissionEvidence, repo: RepositoryEvidence | None) -> bool:
    if not launch.validated:
        return False
    if repo is None or launch.repository is None:
        return True
    return launch.repository == repo.repository


def _latest_progress(
    snapshot: ContinuitySnapshot,
    durable_ok: bool,
    colony_ok: bool,
    provider_ok: bool,
    launch_ok: bool,
) -> tuple[str, str] | None:
    candidates: list[tuple[datetime, str, str]] = []
    repo = snapshot.repository
    if repo and repo.latest_related_commit and repo.latest_related_commit_at:
        dt = _parse_time(repo.latest_related_commit_at)
        if dt:
            candidates.append((dt, "repository_commit", repo.latest_related_commit))
    if durable_ok and snapshot.durable and snapshot.durable.last_progress_at:
        dt = _parse_time(snapshot.durable.last_progress_at)
        if dt:
            candidates.append((dt, "durable_state", snapshot.durable.current_frontier or "durable"))
    if colony_ok and snapshot.build_colony and snapshot.build_colony.last_progress_at:
        dt = _parse_time(snapshot.build_colony.last_progress_at)
        if dt:
            candidates.append((dt, "build_colony", snapshot.build_colony.current_frontier or "build-colony"))
    provider = snapshot.provider
    if provider_ok and provider and provider.state in {ProviderState.ACTIVE, ProviderState.COMPLETED} and provider.observed_at:
        dt = _parse_time(provider.observed_at)
        if dt:
            candidates.append((dt, "provider", provider.provider))
    launch = snapshot.launch_admission
    if launch_ok and launch and launch.observed_at:
        dt = _parse_time(launch.observed_at)
        if dt:
            candidates.append((dt, "launch_admission", launch.receipt_ref))
    if not candidates:
        return None
    dt, kind, ref = max(candidates, key=lambda item: item[0])
    return dt.isoformat(), f"{kind}:{ref}"


def _infrastructure(snapshot: ContinuitySnapshot, provider_ok: bool) -> InfrastructureStatus:
    provider = snapshot.provider
    if provider is None:
        return InfrastructureStatus.NO_PROVIDER_EVIDENCE
    if not provider_ok:
        return InfrastructureStatus.MISMATCHED_EVIDENCE
    if provider.state is ProviderState.UNAVAILABLE:
        return InfrastructureStatus.PROVIDER_RUNNER_UNAVAILABLE
    if provider.state is ProviderState.FAILED and provider.failure_scope is FailureScope.PROVIDER:
        return InfrastructureStatus.PROVIDER_FAILURE
    if provider.state in {ProviderState.ACTIVE, ProviderState.COMPLETED, ProviderState.QUEUED}:
        return InfrastructureStatus.HEALTHY
    return InfrastructureStatus.UNKNOWN


def _action(verdict: DevelopmentVerdict, integration_required: bool) -> RecommendedAction:
    if verdict is DevelopmentVerdict.DONE_CANONICAL:
        return RecommendedAction.NO_ACTION_DONE
    if verdict is DevelopmentVerdict.DONE_TECHNICAL:
        return RecommendedAction.RECONCILE_CANONICAL_STATE if integration_required else RecommendedAction.NO_ACTION_DONE
    if verdict in {DevelopmentVerdict.DEVELOPMENT_PROGRESSING, DevelopmentVerdict.CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED}:
        return RecommendedAction.NO_ACTION_ACTIVE_EXECUTION
    if verdict in {DevelopmentVerdict.CHECKPOINTED_RESUMABLE, DevelopmentVerdict.DEVELOPMENT_STALLED}:
        return RecommendedAction.RESUME_DURABLE_EXECUTION
    if verdict is DevelopmentVerdict.CONDITION_WAIT:
        return RecommendedAction.WAIT_FOR_CONDITION
    if verdict is DevelopmentVerdict.SCHEDULED_WAIT:
        return RecommendedAction.WAIT_UNTIL_SCHEDULED_CHECKPOINT
    if verdict is DevelopmentVerdict.HUMAN_GATE:
        return RecommendedAction.REQUEST_HUMAN_ACTION
    if verdict is DevelopmentVerdict.EXTERNAL_EVIDENCE_GATE:
        return RecommendedAction.REQUEST_EXTERNAL_EVIDENCE
    if verdict is DevelopmentVerdict.FAILED:
        return RecommendedAction.INVESTIGATE_FAILURE
    return RecommendedAction.INSUFFICIENT_EVIDENCE


def inspect_continuity(snapshot: ContinuitySnapshot) -> ContinuityReport:
    resolution = resolve_workstream(snapshot.query, snapshot.candidates)
    warnings: list[str] = []
    if resolution.candidate is None:
        warnings.append(f"workstream_identity_{resolution.status.lower()}")
        return ContinuityReport(
            schema=SCHEMA_VERSION,
            workstream=snapshot.query,
            workstream_id=None,
            checked_at=snapshot.checked_at,
            conversation_assessment=snapshot.conversation.assessment.value,
            development_verdict=DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value,
            repository=snapshot.repository.repository if snapshot.repository else None,
            main_revision=snapshot.repository.main_revision if snapshot.repository else None,
            branch=snapshot.repository.branch if snapshot.repository else None,
            branch_head=snapshot.repository.branch_head if snapshot.repository else None,
            pull_request=None,
            durable_state=None,
            latest_execution_evidence=None,
            blocking_gate=None,
            infrastructure_status=InfrastructureStatus.UNKNOWN.value,
            evidence_warnings=tuple(warnings),
            recommended_action=RecommendedAction.INSUFFICIENT_EVIDENCE.value,
            canonical_state_reconciliation_recommended=False,
        )

    identity = resolution.candidate
    repo = snapshot.repository
    if repo and identity.repository and repo.repository != identity.repository:
        warnings.append("repository_identity_mismatch")
        repo = None

    durable_ok = bool(snapshot.durable and snapshot.durable.workstream_id == identity.workstream_id and _durable_matches_repo(snapshot.durable, repo))
    colony_ok = bool(snapshot.build_colony and snapshot.build_colony.workstream_id == identity.workstream_id and _build_colony_matches_repo(snapshot.build_colony, repo))
    provider_ok = bool(snapshot.provider and _provider_matches_repo(snapshot.provider, repo))
    launch_ok = bool(
        snapshot.launch_admission
        and snapshot.launch_admission.workstream_id == identity.workstream_id
        and _launch_matches_repo(snapshot.launch_admission, repo)
    )
    if snapshot.durable and not durable_ok:
        warnings.append("durable_state_mismatch_or_unvalidated")
    if snapshot.build_colony and not colony_ok:
        warnings.append("build_colony_state_mismatch_or_unvalidated")
    if snapshot.provider and not provider_ok:
        warnings.append("provider_evidence_revision_mismatch")
    if snapshot.launch_admission and not launch_ok:
        warnings.append("launch_admission_mismatch_or_unvalidated")

    infrastructure = _infrastructure(snapshot, provider_ok)
    unsatisfied = [gate for gate in snapshot.gates if not gate.satisfied]
    human_gate = next((gate for gate in unsatisfied if gate.kind is GateKind.HUMAN), None)
    external_gate = next((gate for gate in unsatisfied if gate.kind is GateKind.EXTERNAL_EVIDENCE), None)

    latest = _latest_progress(snapshot, durable_ok, colony_ok, provider_ok, launch_ok)
    latest_exec = {"observed_at": latest[0], "ref": latest[1]} if latest else None

    technical_terminal = None
    if durable_ok and snapshot.durable and snapshot.durable.terminal_verdict:
        technical_terminal = snapshot.durable.terminal_verdict
    elif colony_ok and snapshot.build_colony and snapshot.build_colony.terminal_verdict:
        technical_terminal = snapshot.build_colony.terminal_verdict

    canonical_done = bool(repo and repo.pull_request_merged and repo.canonical_contains_workstream)
    workload_failure = bool(
        (durable_ok and snapshot.durable and snapshot.durable.failed_terminal_reason)
        or (provider_ok and snapshot.provider and snapshot.provider.state is ProviderState.FAILED and snapshot.provider.failure_scope is FailureScope.WORKLOAD)
    )

    active_execution = bool(
        (durable_ok and snapshot.durable and snapshot.durable.active_dispatch)
        or (provider_ok and snapshot.provider and snapshot.provider.state is ProviderState.ACTIVE)
    )

    verdict: DevelopmentVerdict
    gate: GateEvidence | None = None

    launch = snapshot.launch_admission if launch_ok else None

    if canonical_done:
        verdict = DevelopmentVerdict.DONE_CANONICAL
    elif human_gate is not None:
        verdict = DevelopmentVerdict.HUMAN_GATE
        gate = human_gate
    elif external_gate is not None:
        verdict = DevelopmentVerdict.EXTERNAL_EVIDENCE_GATE
        gate = external_gate
    elif launch and launch.disposition is LaunchDisposition.HUMAN_GATE:
        verdict = DevelopmentVerdict.HUMAN_GATE
    elif durable_ok and snapshot.durable and snapshot.durable.scheduled_checkpoint:
        verdict = DevelopmentVerdict.SCHEDULED_WAIT
    elif durable_ok and snapshot.durable and snapshot.durable.wake_condition:
        verdict = DevelopmentVerdict.CONDITION_WAIT
    elif workload_failure:
        verdict = DevelopmentVerdict.FAILED
    elif launch and launch.disposition in {
        LaunchDisposition.REJECTED,
        LaunchDisposition.FAILED_BEFORE_LAUNCH,
    }:
        verdict = DevelopmentVerdict.FAILED
    elif technical_terminal:
        verdict = DevelopmentVerdict.DONE_TECHNICAL
    elif active_execution:
        conversation_time = _parse_time(snapshot.conversation.last_observed_at)
        latest_time = _parse_time(latest[0]) if latest else None
        if (
            snapshot.conversation.assessment is ConversationAssessment.INTERRUPTION_SUSPECTED
            and conversation_time is not None
            and latest_time is not None
            and latest_time > conversation_time
        ):
            verdict = DevelopmentVerdict.CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED
        else:
            verdict = DevelopmentVerdict.DEVELOPMENT_PROGRESSING
    elif durable_ok and snapshot.durable and snapshot.durable.admissible_next:
        if snapshot.durable.execution_expected and snapshot.durable.recovery_semantics_exhausted:
            verdict = DevelopmentVerdict.DEVELOPMENT_STALLED
        else:
            verdict = DevelopmentVerdict.CHECKPOINTED_RESUMABLE
    elif colony_ok and snapshot.build_colony and snapshot.build_colony.admissible_next:
        verdict = DevelopmentVerdict.CHECKPOINTED_RESUMABLE
    elif launch and launch.disposition is LaunchDisposition.ADMITTED:
        verdict = (
            DevelopmentVerdict.DEVELOPMENT_STALLED
            if launch.recovery_semantics_exhausted
            else DevelopmentVerdict.CHECKPOINTED_RESUMABLE
        )
    else:
        verdict = DevelopmentVerdict.INSUFFICIENT_EVIDENCE

    pull_request = None
    if repo and repo.pull_request_number is not None:
        pull_request = {
            "number": repo.pull_request_number,
            "state": repo.pull_request_state,
            "mergeable": repo.pull_request_mergeable,
            "merged": repo.pull_request_merged,
        }

    durable_state = None
    if durable_ok and snapshot.durable:
        durable_state = {
            "current_frontier": snapshot.durable.current_frontier,
            "completed": list(snapshot.durable.completed_frontiers),
            "admissible_next": list(snapshot.durable.admissible_next),
            "wake_condition": snapshot.durable.wake_condition,
            "scheduled_checkpoint": snapshot.durable.scheduled_checkpoint,
            "terminal_verdict": snapshot.durable.terminal_verdict,
        }

    blocking_gate = None
    if gate:
        blocking_gate = {"kind": gate.kind.value, "ref": gate.ref, "reason": gate.reason, "frontier": gate.frontier}
    elif launch and launch.disposition is LaunchDisposition.HUMAN_GATE:
        blocking_gate = {
            "kind": "HUMAN",
            "ref": launch.receipt_ref,
            "reason": launch.detail or "execution launch authority gate",
            "frontier": launch.launch_id or "execution-launch-admission",
        }
    elif verdict is DevelopmentVerdict.SCHEDULED_WAIT and snapshot.durable:
        blocking_gate = {"kind": "SCHEDULED", "ref": snapshot.durable.scheduled_checkpoint, "reason": "scheduled checkpoint", "frontier": snapshot.durable.current_frontier}
    elif verdict is DevelopmentVerdict.CONDITION_WAIT and snapshot.durable:
        blocking_gate = {"kind": "CONDITION", "ref": snapshot.durable.wake_condition, "reason": "observable wake condition", "frontier": snapshot.durable.current_frontier}
    elif verdict is DevelopmentVerdict.FAILED:
        reason = None
        failure_ref = "failure://continuity-check"
        frontier = snapshot.durable.current_frontier if snapshot.durable else None
        if durable_ok and snapshot.durable:
            reason = snapshot.durable.failed_terminal_reason
        if reason is None and snapshot.provider:
            reason = snapshot.provider.detail
        if launch and launch.disposition in {
            LaunchDisposition.REJECTED,
            LaunchDisposition.FAILED_BEFORE_LAUNCH,
        }:
            reason = launch.detail or launch.disposition.value
            failure_ref = launch.receipt_ref
            frontier = launch.launch_id or "execution-launch-admission"
        blocking_gate = {
            "kind": "FAILURE",
            "ref": failure_ref,
            "reason": reason or "explicit workload failure",
            "frontier": frontier,
        }

    action = _action(verdict, snapshot.canonical_integration_required)
    return ContinuityReport(
        schema=SCHEMA_VERSION,
        workstream=identity.canonical_name,
        workstream_id=identity.workstream_id,
        checked_at=snapshot.checked_at,
        conversation_assessment=snapshot.conversation.assessment.value,
        development_verdict=verdict.value,
        repository=repo.repository if repo else None,
        main_revision=repo.main_revision if repo else None,
        branch=repo.branch if repo else identity.branch,
        branch_head=repo.branch_head if repo else None,
        pull_request=pull_request,
        durable_state=durable_state,
        latest_execution_evidence=latest_exec,
        blocking_gate=blocking_gate,
        infrastructure_status=infrastructure.value,
        evidence_warnings=tuple(warnings),
        recommended_action=action.value,
        canonical_state_reconciliation_recommended=(verdict is DevelopmentVerdict.DONE_TECHNICAL and snapshot.canonical_integration_required),
    )


def render_report(report: ContinuityReport) -> str:
    status = {
        DevelopmentVerdict.DEVELOPMENT_PROGRESSING.value: "🟢",
        DevelopmentVerdict.CONVERSATION_INTERRUPTED_DEVELOPMENT_CONTINUED.value: "🟢",
        DevelopmentVerdict.CHECKPOINTED_RESUMABLE.value: "🟢",
        DevelopmentVerdict.CONDITION_WAIT.value: "🟡",
        DevelopmentVerdict.SCHEDULED_WAIT.value: "🟡",
        DevelopmentVerdict.HUMAN_GATE.value: "🟡",
        DevelopmentVerdict.EXTERNAL_EVIDENCE_GATE.value: "🟡",
        DevelopmentVerdict.DONE_TECHNICAL.value: "🟢",
        DevelopmentVerdict.DONE_CANONICAL.value: "🟢",
        DevelopmentVerdict.DEVELOPMENT_STALLED.value: "🟠",
        DevelopmentVerdict.FAILED.value: "🔴",
        DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value: "⚪",
    }.get(report.development_verdict, "⚪")
    conversation = report.conversation_assessment.replace("CONVERSATION_", "").lower().replace("_", " ")
    lines = [
        "Continuity Check",
        "",
        f"Workstream: {report.workstream}",
        f"Conversation: {conversation}",
        f"Development: {status} {report.development_verdict}",
    ]
    if report.repository:
        lines.append(f"Repository: {report.repository}")
    if report.branch:
        lines.append(f"Branch: {report.branch}")
    if report.branch_head:
        lines.append(f"Latest verified: {report.branch_head[:12]}…")
    if report.pull_request:
        pr = report.pull_request
        lines.append(f"PR: #{pr['number']} {pr.get('state') or 'UNKNOWN'} / mergeable={pr.get('mergeable')}")
    if report.durable_state:
        ds = report.durable_state
        if ds.get("current_frontier"):
            lines.append(f"Durable frontier: {ds['current_frontier']}")
        if ds.get("admissible_next"):
            lines.append("Next admissible: " + " → ".join(ds["admissible_next"]))
    if report.blocking_gate:
        lines.append(f"Blocking gate: {report.blocking_gate['kind']} — {report.blocking_gate['ref']}")
    else:
        lines.append("Blocking gate: none")
    lines.append(f"Infrastructure: {report.infrastructure_status}")
    if report.conversation_assessment == ConversationAssessment.INTERRUPTION_SUSPECTED.value and report.development_verdict not in {DevelopmentVerdict.FAILED.value, DevelopmentVerdict.INSUFFICIENT_EVIDENCE.value}:
        lines.extend(["", "Verdict: conversation interruption ≠ development interruption"])
    lines.append(f"Action: {report.recommended_action}")
    return "\n".join(lines)
