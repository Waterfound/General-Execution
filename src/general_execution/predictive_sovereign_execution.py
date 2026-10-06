from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable

from .canonical import sha256_digest

PRECOMPUTE_SCHEMA = "ge.predictive-precomputation-plan.v1"
RECOVERY_SCHEMA = "ge.sovereign-recovery-capsule.v1"
FORECAST_SCHEMA = "ge.gate-forecast.v1"
VERIFY_SCHEMA = "ge.independent-verification-observation.v1"
VERIFY_RECONCILIATION_SCHEMA = "ge.independent-verification-reconciliation.v1"
SUBSTITUTION_SCHEMA = "ge.capability-substitution-decision.v1"


class PredictiveSovereignError(ValueError):
    pass


class GateKind(str, Enum):
    HUMAN_AUTHORITY = "human_authority"
    REAUTHENTICATION = "reauthentication"
    EXTERNAL_EVIDENCE = "external_evidence"
    CAPACITY = "capacity"
    TIME = "time"
    SHARED_STATE = "shared_state"
    PAID_RESOURCE = "paid_resource"
    PHYSICAL_ACTION = "physical_action"


class VerificationVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PredictiveSovereignError(f"{field} must be a non-empty string")
    return value.strip()


def _digest(value: str, field: str) -> str:
    value = _nonempty(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise PredictiveSovereignError(f"{field} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise PredictiveSovereignError(f"{field} must contain hexadecimal digest") from exc
    return value


def _nonnegative(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PredictiveSovereignError(f"{field} must be a non-negative integer")
    return value


def _unique(values: Iterable[str], field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(_nonempty(item, field) for item in values)
    if not allow_empty and not items:
        raise PredictiveSovereignError(f"{field} cannot be empty")
    if len(items) != len(set(items)):
        raise PredictiveSovereignError(f"{field} must not contain duplicates")
    return items


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class PredictiveTask:
    task_id: str
    evidence_predicate: str
    depends_on: tuple[str, ...] = ()
    shared_state_keys: tuple[str, ...] = ()
    side_effect_free: bool = True
    irreversible: bool = False
    requires_authority: bool = False
    requires_observed_gate_outcome: bool = False

    def __post_init__(self) -> None:
        _nonempty(self.task_id, "task_id")
        _nonempty(self.evidence_predicate, "evidence_predicate")
        _unique(self.depends_on, "depends_on")
        _unique(self.shared_state_keys, "shared_state_keys")
        for name in (
            "side_effect_free",
            "irreversible",
            "requires_authority",
            "requires_observed_gate_outcome",
        ):
            if not isinstance(getattr(self, name), bool):
                raise PredictiveSovereignError(f"{name} must be boolean")


@dataclass(frozen=True, slots=True)
class PredictivePrecomputationPlan:
    current_gate_ref: str
    selected_task_ids: tuple[str, ...]
    deferred_task_ids: tuple[str, ...]
    waves: tuple[tuple[str, ...], ...]
    reasons: tuple[tuple[str, tuple[str, ...]], ...]
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = PRECOMPUTE_SCHEMA

    def __post_init__(self) -> None:
        _nonempty(self.current_gate_ref, "current_gate_ref")
        if self.authority_created or self.execution_triggered:
            raise PredictiveSovereignError("precomputation cannot create authority or trigger execution")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def build_precomputation_plan(
    current_gate_ref: str,
    tasks: tuple[PredictiveTask, ...],
    *,
    already_materialized: tuple[str, ...] = (),
) -> PredictivePrecomputationPlan:
    _nonempty(current_gate_ref, "current_gate_ref")
    materialized = set(_unique(already_materialized, "already_materialized"))
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        raise PredictiveSovereignError("task_id values must be unique")
    known = set(ids) | materialized
    for task in tasks:
        unknown = set(task.depends_on) - known
        if unknown:
            raise PredictiveSovereignError(
                f"task {task.task_id} has unknown dependencies: {sorted(unknown)}"
            )

    eligible: dict[str, PredictiveTask] = {}
    reasons: dict[str, tuple[str, ...]] = {}
    for task in tasks:
        why: list[str] = []
        if not task.side_effect_free:
            why.append("side_effectful")
        if task.irreversible:
            why.append("irreversible")
        if task.requires_authority:
            why.append("requires_authority")
        if task.requires_observed_gate_outcome:
            why.append("requires_observed_gate_outcome")
        if why:
            reasons[task.task_id] = tuple(sorted(why))
        else:
            eligible[task.task_id] = task

    selected: set[str] = set()
    waves: list[tuple[str, ...]] = []
    remaining = set(eligible)
    satisfied = set(materialized)
    while remaining:
        ready = sorted(
            task_id
            for task_id in remaining
            if set(eligible[task_id].depends_on) <= (satisfied | selected)
        )
        if not ready:
            break

        wave: list[str] = []
        used_keys: set[str] = set()
        for task_id in ready:
            keys = set(eligible[task_id].shared_state_keys)
            if keys & used_keys:
                continue
            wave.append(task_id)
            used_keys |= keys

        if not wave:
            wave = [ready[0]]

        wave_tuple = tuple(wave)
        waves.append(wave_tuple)
        selected.update(wave_tuple)
        remaining -= set(wave_tuple)

    for task_id in sorted(remaining):
        reasons[task_id] = tuple(sorted(set(reasons.get(task_id, ())) | {"dependency_not_precomputable"}))

    deferred = tuple(sorted(set(ids) - selected))
    ordered_reasons = tuple((task_id, reasons.get(task_id, ())) for task_id in deferred)
    return PredictivePrecomputationPlan(
        current_gate_ref=current_gate_ref,
        selected_task_ids=tuple(task_id for wave in waves for task_id in wave),
        deferred_task_ids=deferred,
        waves=tuple(waves),
        reasons=ordered_reasons,
    )


@dataclass(frozen=True, slots=True)
class SovereignRecoveryCapsule:
    capsule_id: str
    source_refs: tuple[str, ...]
    durable_state_digests: tuple[str, ...]
    authority_refs: tuple[str, ...]
    resource_aliases: tuple[str, ...]
    reconstruction_steps: tuple[str, ...]
    verification_predicates: tuple[str, ...]
    secret_material_persisted: bool = False
    authority_created: bool = False
    schema_version: str = RECOVERY_SCHEMA

    def __post_init__(self) -> None:
        _nonempty(self.capsule_id, "capsule_id")
        _unique(self.source_refs, "source_refs", allow_empty=False)
        _unique(self.durable_state_digests, "durable_state_digests", allow_empty=False)
        for index, value in enumerate(self.durable_state_digests):
            _digest(value, f"durable_state_digests[{index}]")
        _unique(self.authority_refs, "authority_refs")
        _unique(self.resource_aliases, "resource_aliases")
        _unique(self.reconstruction_steps, "reconstruction_steps", allow_empty=False)
        _unique(self.verification_predicates, "verification_predicates", allow_empty=False)
        if self.secret_material_persisted:
            raise PredictiveSovereignError("recovery capsule cannot persist secret material")
        if self.authority_created:
            raise PredictiveSovereignError("recovery capsule cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def build_recovery_capsule(
    *,
    capsule_id: str,
    source_refs: tuple[str, ...],
    durable_state_digests: tuple[str, ...],
    authority_refs: tuple[str, ...],
    resource_aliases: tuple[str, ...],
    reconstruction_steps: tuple[str, ...],
    verification_predicates: tuple[str, ...],
    secret_material: tuple[str, ...] = (),
) -> SovereignRecoveryCapsule:
    if secret_material:
        raise PredictiveSovereignError("secret material is forbidden in recovery capsule")
    return SovereignRecoveryCapsule(
        capsule_id=capsule_id,
        source_refs=source_refs,
        durable_state_digests=durable_state_digests,
        authority_refs=authority_refs,
        resource_aliases=resource_aliases,
        reconstruction_steps=reconstruction_steps,
        verification_predicates=verification_predicates,
    )


@dataclass(frozen=True, slots=True)
class GateCandidate:
    gate_ref: str
    kind: GateKind
    distance: int
    dependency_ref: str
    evidence_basis: tuple[str, ...]
    human_action_likely: bool = False

    def __post_init__(self) -> None:
        _nonempty(self.gate_ref, "gate_ref")
        _nonempty(self.dependency_ref, "dependency_ref")
        _nonnegative(self.distance, "distance")
        _unique(self.evidence_basis, "evidence_basis", allow_empty=False)
        if not isinstance(self.human_action_likely, bool):
            raise PredictiveSovereignError("human_action_likely must be boolean")


@dataclass(frozen=True, slots=True)
class GateForecast:
    gates: tuple[GateCandidate, ...]
    compilation_refs: tuple[str, ...]
    advisory_only: bool = True
    authority_created: bool = False
    schema_version: str = FORECAST_SCHEMA

    def __post_init__(self) -> None:
        if not self.advisory_only:
            raise PredictiveSovereignError("gate forecast must remain advisory")
        if self.authority_created:
            raise PredictiveSovereignError("gate forecast cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def forecast_gates(candidates: tuple[GateCandidate, ...]) -> GateForecast:
    refs = [candidate.gate_ref for candidate in candidates]
    if len(refs) != len(set(refs)):
        raise PredictiveSovereignError("gate_ref values must be unique")
    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.distance,
                0 if item.human_action_likely else 1,
                item.kind.value,
                item.gate_ref,
            ),
        )
    )
    compilation = tuple(
        candidate.gate_ref
        for candidate in ordered
        if candidate.human_action_likely
        or candidate.kind in {
            GateKind.HUMAN_AUTHORITY,
            GateKind.REAUTHENTICATION,
            GateKind.PAID_RESOURCE,
            GateKind.PHYSICAL_ACTION,
        }
    )
    return GateForecast(gates=ordered, compilation_refs=compilation)


@dataclass(frozen=True, slots=True)
class VerificationObservation:
    verifier_id: str
    materialization_id: str
    predicate_digest: str
    verdict: VerificationVerdict
    evidence_digest: str
    authority_created: bool = False
    schema_version: str = VERIFY_SCHEMA

    def __post_init__(self) -> None:
        _nonempty(self.verifier_id, "verifier_id")
        _nonempty(self.materialization_id, "materialization_id")
        _digest(self.predicate_digest, "predicate_digest")
        _digest(self.evidence_digest, "evidence_digest")
        if self.authority_created:
            raise PredictiveSovereignError("verification observation cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class VerificationReconciliation:
    predicate_digest: str
    status: str
    primary_digest: str
    twin_digest: str
    independent: bool
    promotable: bool
    authority_created: bool = False
    schema_version: str = VERIFY_RECONCILIATION_SCHEMA

    def __post_init__(self) -> None:
        _digest(self.predicate_digest, "predicate_digest")
        _digest(self.primary_digest, "primary_digest")
        _digest(self.twin_digest, "twin_digest")
        if self.promotable and self.status != "AGREEMENT_PASS":
            raise PredictiveSovereignError("only AGREEMENT_PASS can be promotable")
        if self.authority_created:
            raise PredictiveSovereignError("verification reconciliation cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def reconcile_verification_twin(
    primary: VerificationObservation,
    twin: VerificationObservation,
) -> VerificationReconciliation:
    if primary.predicate_digest != twin.predicate_digest:
        raise PredictiveSovereignError("verification predicate mismatch")
    independent = (
        primary.verifier_id != twin.verifier_id
        and primary.materialization_id != twin.materialization_id
    )
    if not independent:
        status = "NOT_INDEPENDENT"
        promotable = False
    elif primary.verdict is VerificationVerdict.FAIL or twin.verdict is VerificationVerdict.FAIL:
        status = "AGREEMENT_FAIL" if primary.verdict is twin.verdict else "DISAGREEMENT"
        promotable = False
    elif (
        primary.verdict is VerificationVerdict.PASS
        and twin.verdict is VerificationVerdict.PASS
    ):
        status = "AGREEMENT_PASS"
        promotable = True
    else:
        status = "RECONCILIATION_REQUIRED"
        promotable = False
    return VerificationReconciliation(
        predicate_digest=primary.predicate_digest,
        status=status,
        primary_digest=primary.digest,
        twin_digest=twin.digest,
        independent=independent,
        promotable=promotable,
    )


@dataclass(frozen=True, slots=True)
class CapabilityMethod:
    method_id: str
    evidence_predicates: tuple[str, ...]
    authority_refs: tuple[str, ...]
    cost_rank: int
    paid_spend_cents: int = 0
    available: bool = True
    evidence_quality_rank: int = 0
    authority_created: bool = False

    def __post_init__(self) -> None:
        _nonempty(self.method_id, "method_id")
        _unique(self.evidence_predicates, "evidence_predicates", allow_empty=False)
        _unique(self.authority_refs, "authority_refs", allow_empty=False)
        _nonnegative(self.cost_rank, "cost_rank")
        _nonnegative(self.paid_spend_cents, "paid_spend_cents")
        _nonnegative(self.evidence_quality_rank, "evidence_quality_rank")
        if not isinstance(self.available, bool):
            raise PredictiveSovereignError("available must be boolean")
        if self.authority_created:
            raise PredictiveSovereignError("capability method cannot create authority")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class CapabilitySubstitutionDecision:
    predicate: str
    selected_method_id: str | None
    rejected: tuple[tuple[str, tuple[str, ...]], ...]
    deferred: bool
    evidence_predicate_preserved: bool
    authority_created: bool = False
    execution_triggered: bool = False
    schema_version: str = SUBSTITUTION_SCHEMA

    def __post_init__(self) -> None:
        _nonempty(self.predicate, "predicate")
        if self.deferred != (self.selected_method_id is None):
            raise PredictiveSovereignError("deferred must match selection state")
        if self.authority_created or self.execution_triggered:
            raise PredictiveSovereignError("substitution cannot create authority or trigger execution")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def select_capability_substitute(
    *,
    predicate: str,
    methods: tuple[CapabilityMethod, ...],
    allowed_method_ids: tuple[str, ...],
    active_authority_refs: tuple[str, ...],
    max_paid_spend_cents: int = 0,
    minimum_evidence_quality_rank: int = 0,
) -> CapabilitySubstitutionDecision:
    _nonempty(predicate, "predicate")
    allowed = set(_unique(allowed_method_ids, "allowed_method_ids", allow_empty=False))
    authorities = set(_unique(active_authority_refs, "active_authority_refs", allow_empty=False))
    _nonnegative(max_paid_spend_cents, "max_paid_spend_cents")
    _nonnegative(minimum_evidence_quality_rank, "minimum_evidence_quality_rank")

    ids = [method.method_id for method in methods]
    if len(ids) != len(set(ids)):
        raise PredictiveSovereignError("method_id values must be unique")

    eligible: list[CapabilityMethod] = []
    rejected: list[tuple[str, tuple[str, ...]]] = []
    for method in methods:
        reasons: list[str] = []
        if method.method_id not in allowed:
            reasons.append("method_outside_authority")
        if predicate not in method.evidence_predicates:
            reasons.append("predicate_not_covered")
        if not set(method.authority_refs) <= authorities:
            reasons.append("authority_ref_not_active")
        if not method.available:
            reasons.append("method_unavailable")
        if method.paid_spend_cents > max_paid_spend_cents:
            reasons.append("paid_spend_exceeds_envelope")
        if method.evidence_quality_rank < minimum_evidence_quality_rank:
            reasons.append("evidence_quality_insufficient")
        if reasons:
            rejected.append((method.method_id, tuple(sorted(set(reasons)))))
        else:
            eligible.append(method)

    if not eligible:
        return CapabilitySubstitutionDecision(
            predicate=predicate,
            selected_method_id=None,
            rejected=tuple(sorted(rejected)),
            deferred=True,
            evidence_predicate_preserved=False,
        )

    selected = min(
        eligible,
        key=lambda method: (
            method.paid_spend_cents,
            method.cost_rank,
            -method.evidence_quality_rank,
            method.method_id,
        ),
    )
    return CapabilitySubstitutionDecision(
        predicate=predicate,
        selected_method_id=selected.method_id,
        rejected=tuple(sorted(rejected)),
        deferred=False,
        evidence_predicate_preserved=True,
    )
