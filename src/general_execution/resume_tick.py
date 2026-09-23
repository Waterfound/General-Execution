from __future__ import annotations

from dataclasses import dataclass

from .asp_transition import (
    PassiveWakeAdmission,
    PortfolioTransitionResult,
    TransitionAuthorityGrant,
    apply_active_transition,
)
from .canonical import sha256_digest, stable_id
from .execution_checkpoint import CheckpointEvidence
from .portfolio_persistence import (
    PortfolioPersistenceError,
    SqlitePortfolioHeadStore,
    recover_portfolio_after_restart,
)
from .transition_policy import TransitionPolicy

CORE_VERIFICATION_SCHEMA = "ge.core-verification-receipt.v1"
TICK_OBSERVATION_SCHEMA = "ge.resume-tick-observation.v1"
TICK_RESULT_SCHEMA = "ge.resume-tick-result.v1"

TickDisposition = str


class ResumeTickError(ValueError):
    pass


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ResumeTickError(f"{name} must be a non-empty string")


def _digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ResumeTickError(f"{name} must be sha256:<64-hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ResumeTickError(
            f"{name} must contain 64 hexadecimal characters"
        ) from exc


def _commit_sha(name: str, value: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise ResumeTickError(f"{name} must be a 40-character commit SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ResumeTickError(f"{name} must be hexadecimal") from exc


@dataclass(frozen=True, slots=True)
class CoreVerificationReceipt:
    target_revision: str
    suite_ref: str
    evidence_ref: str
    evidence_digest: str
    verifier_ref: str
    executed_at: str
    passed: bool
    test_count: int
    schema_version: str = CORE_VERIFICATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CORE_VERIFICATION_SCHEMA:
            raise ResumeTickError("unsupported core verification receipt schema")
        _commit_sha("target_revision", self.target_revision)
        for name in ("suite_ref", "evidence_ref", "verifier_ref", "executed_at"):
            _nonempty(name, getattr(self, name))
        _digest("evidence_digest", self.evidence_digest)
        if not isinstance(self.passed, bool):
            raise ResumeTickError("passed must be boolean")
        if not isinstance(self.test_count, int) or isinstance(self.test_count, bool):
            raise ResumeTickError("test_count must be an integer")
        if self.test_count < 1:
            raise ResumeTickError("test_count must be >= 1")
        if not self.passed:
            raise ResumeTickError("core verification receipt must record PASS")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


@dataclass(frozen=True, slots=True)
class ResumeTickObservation:
    portfolio_id: str
    expected_generation: int
    expected_state_digest: str
    event: str
    evidence: tuple[CheckpointEvidence, ...]
    action_ref: str
    observed_at: str
    summary: str
    canonical_refs: tuple[str, ...]
    uncertainties: tuple[str, ...] = ()
    wake_admission: PassiveWakeAdmission | None = None
    authority_grant: TransitionAuthorityGrant | None = None
    schema_version: str = TICK_OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != TICK_OBSERVATION_SCHEMA:
            raise ResumeTickError("unsupported resume tick observation schema")
        for name in (
            "portfolio_id",
            "event",
            "action_ref",
            "observed_at",
            "summary",
        ):
            _nonempty(name, getattr(self, name))
        if not isinstance(self.expected_generation, int) or isinstance(
            self.expected_generation, bool
        ):
            raise ResumeTickError("expected_generation must be an integer")
        if self.expected_generation < 0:
            raise ResumeTickError("expected_generation cannot be negative")
        _digest("expected_state_digest", self.expected_state_digest)
        if not self.evidence:
            raise ResumeTickError("tick observation requires admitted evidence")
        identities = tuple(item.identity for item in self.evidence)
        if len(identities) != len(set(identities)):
            raise ResumeTickError("tick observation evidence must be unique")
        if not self.canonical_refs:
            raise ResumeTickError("tick observation requires canonical_refs")
        if any(not isinstance(value, str) or not value.strip() for value in self.canonical_refs):
            raise ResumeTickError("canonical_refs must contain non-empty strings")
        if len(self.canonical_refs) != len(set(self.canonical_refs)):
            raise ResumeTickError("canonical_refs must be unique")
        if any(not isinstance(value, str) or not value.strip() for value in self.uncertainties):
            raise ResumeTickError("uncertainties must contain non-empty strings")
        if len(self.uncertainties) != len(set(self.uncertainties)):
            raise ResumeTickError("uncertainties must be unique")

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def observation_id(self) -> str:
        return stable_id("getick", self)

    @property
    def checkpoint_ref(self) -> str:
        return f"tick-observation:{self.digest}"


@dataclass(frozen=True, slots=True)
class ResumeTickResult:
    portfolio_id: str
    disposition: TickDisposition
    observation_digest: str
    pre_generation: int
    post_generation: int
    pre_state_digest: str
    post_state_digest: str
    checkpoint_digest: str | None = None
    transition_result_digest: str | None = None
    recovery_report_digest: str | None = None
    schema_version: str = TICK_RESULT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != TICK_RESULT_SCHEMA:
            raise ResumeTickError("unsupported resume tick result schema")
        _nonempty("portfolio_id", self.portfolio_id)
        if self.disposition not in {
            "committed",
            "already_applied",
            "external_input_required",
            "verification_gate_closed",
            "stale_observation",
        }:
            raise ResumeTickError("unsupported tick disposition")
        _digest("observation_digest", self.observation_digest)
        _digest("pre_state_digest", self.pre_state_digest)
        _digest("post_state_digest", self.post_state_digest)
        for name in (
            "checkpoint_digest",
            "transition_result_digest",
            "recovery_report_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                _digest(name, value)
        for name in ("pre_generation", "post_generation"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ResumeTickError(f"{name} must be a non-negative integer")

        if self.disposition == "committed":
            if self.post_generation != self.pre_generation + 1:
                raise ResumeTickError("committed tick must advance exactly one generation")
            if self.post_state_digest == self.pre_state_digest:
                raise ResumeTickError("committed tick must change state digest")
            if (
                self.checkpoint_digest is None
                or self.transition_result_digest is None
                or self.recovery_report_digest is None
            ):
                raise ResumeTickError("committed tick requires full durable evidence")
        else:
            if self.post_generation != self.pre_generation:
                raise ResumeTickError("non-committed tick cannot advance generation")
            if self.post_state_digest != self.pre_state_digest:
                raise ResumeTickError("non-committed tick cannot mutate state")

    @property
    def digest(self) -> str:
        return sha256_digest(self)


def _gate_open(
    receipt: CoreVerificationReceipt | None,
    required_revision: str,
) -> bool:
    _commit_sha("required_revision", required_revision)
    return (
        receipt is not None
        and receipt.passed
        and receipt.target_revision == required_revision
    )


def _already_applied(
    store: SqlitePortfolioHeadStore,
    portfolio_id: str,
    observation_ref: str,
) -> tuple[bool, str | None, str | None]:
    checkpoint = store.latest_checkpoint(portfolio_id)
    if checkpoint is None:
        return False, None, None
    if observation_ref not in checkpoint.canonical_refs:
        return False, None, None
    return True, checkpoint.digest, None


def resume_tick(
    store: SqlitePortfolioHeadStore,
    portfolio_id: str,
    policy: TransitionPolicy,
    observation: ResumeTickObservation,
    *,
    required_core_revision: str,
    core_verification: CoreVerificationReceipt | None,
) -> ResumeTickResult:
    _nonempty("portfolio_id", portfolio_id)
    if observation.portfolio_id != portfolio_id:
        raise ResumeTickError("tick observation portfolio identity mismatch")

    state, _, recovery = recover_portfolio_after_restart(store, portfolio_id)
    pre_generation = state.generation
    pre_digest = state.digest

    if not _gate_open(core_verification, required_core_revision):
        return ResumeTickResult(
            portfolio_id=portfolio_id,
            disposition="verification_gate_closed",
            observation_digest=observation.digest,
            pre_generation=pre_generation,
            post_generation=pre_generation,
            pre_state_digest=pre_digest,
            post_state_digest=pre_digest,
            recovery_report_digest=recovery.digest,
        )

    applied, checkpoint_digest, _ = _already_applied(
        store,
        portfolio_id,
        observation.checkpoint_ref,
    )
    if applied:
        return ResumeTickResult(
            portfolio_id=portfolio_id,
            disposition="already_applied",
            observation_digest=observation.digest,
            pre_generation=pre_generation,
            post_generation=pre_generation,
            pre_state_digest=pre_digest,
            post_state_digest=pre_digest,
            checkpoint_digest=checkpoint_digest,
            recovery_report_digest=recovery.digest,
        )

    if (
        observation.expected_generation != state.generation
        or observation.expected_state_digest != state.digest
    ):
        return ResumeTickResult(
            portfolio_id=portfolio_id,
            disposition="stale_observation",
            observation_digest=observation.digest,
            pre_generation=pre_generation,
            post_generation=pre_generation,
            pre_state_digest=pre_digest,
            post_state_digest=pre_digest,
            recovery_report_digest=recovery.digest,
        )

    transition: PortfolioTransitionResult = apply_active_transition(
        state,
        policy,
        observation.event,
        observation.evidence,
        action_ref=observation.action_ref,
        observed_at=observation.observed_at,
        summary=observation.summary,
        canonical_refs=(
            *observation.canonical_refs,
            observation.checkpoint_ref,
            f"core-verification:{core_verification.digest}",
        ),
        uncertainties=observation.uncertainties,
        wake_admission=observation.wake_admission,
        authority_grant=observation.authority_grant,
    )

    try:
        store.commit(
            portfolio_id,
            state.digest,
            transition.new_state,
            transition.checkpoint,
        )
    except PortfolioPersistenceError as exc:
        recovered_state, _, recovered_report = recover_portfolio_after_restart(
            store,
            portfolio_id,
        )
        if recovered_state.digest != state.digest:
            return ResumeTickResult(
                portfolio_id=portfolio_id,
                disposition="stale_observation",
                observation_digest=observation.digest,
                pre_generation=recovered_state.generation,
                post_generation=recovered_state.generation,
                pre_state_digest=recovered_state.digest,
                post_state_digest=recovered_state.digest,
                recovery_report_digest=recovered_report.digest,
            )
        raise ResumeTickError("durable tick commit failed without competing state") from exc

    post_state, post_checkpoint, post_recovery = recover_portfolio_after_restart(
        store,
        portfolio_id,
    )
    if post_checkpoint is None:
        raise ResumeTickError("committed tick did not recover a checkpoint")
    if post_checkpoint.digest != transition.checkpoint.digest:
        raise ResumeTickError("committed tick recovered a different checkpoint")
    if post_state != transition.new_state:
        raise ResumeTickError("committed tick recovered a different portfolio state")

    return ResumeTickResult(
        portfolio_id=portfolio_id,
        disposition="committed",
        observation_digest=observation.digest,
        pre_generation=pre_generation,
        post_generation=post_state.generation,
        pre_state_digest=pre_digest,
        post_state_digest=post_state.digest,
        checkpoint_digest=post_checkpoint.digest,
        transition_result_digest=transition.digest,
        recovery_report_digest=post_recovery.digest,
    )
