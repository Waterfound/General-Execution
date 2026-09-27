"""Provider-neutral, one-shot trigger consumption. No listeners or provider calls.

Trust boundary: the host supplies an independently authenticated admission digest.
An event's claim to authenticity is never an admission. Real host activation is
outside this module and requires its own authority and verification gates.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re
import sqlite3

from .canonical import sha256_digest
from .core_rehearsal import CoreRehearsalReport
from .execution_checkpoint import deserialize_checkpoint
from .portfolio_persistence import SqlitePortfolioHeadStore, recover_portfolio_after_restart
from .resume_tick import CoreVerificationReceipt, CoreVerificationRequirement, ResumeTickObservation, ResumeTickResult, resume_tick
from .transition_policy import TransitionPolicy


class TriggerAdmissionError(ValueError):
    pass


def _digest(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise TriggerAdmissionError('invalid digest')


@dataclass(frozen=True, slots=True)
class ExternalTriggerEvidence:
    source: str
    event_id: str
    event_kind: str
    payload_digest: str
    observation_digest: str
    admission_ref: str

    def __post_init__(self):
        for value in (self.source, self.event_id, self.event_kind, self.admission_ref):
            if not isinstance(value, str) or not value.strip():
                raise TriggerAdmissionError('missing trigger provenance')
        _digest(self.payload_digest)
        _digest(self.observation_digest)

    @property
    def digest(self) -> str:
        return sha256_digest(self)

    @property
    def identity(self) -> str:
        return sha256_digest((self.source, self.event_id))


@dataclass(frozen=True, slots=True)
class TriggerContract:
    source: str
    event_kind: str
    portfolio_id: str
    policy_digest: str
    transition_event: str

    def __post_init__(self):
        _digest(self.policy_digest)
        if any(not isinstance(x, str) or not x.strip() for x in (self.source,self.event_kind,self.portfolio_id,self.transition_event)):
            raise TriggerAdmissionError('incomplete trigger contract')


def consume_external_trigger(
    database: str | Path, contract: TriggerContract, event: ExternalTriggerEvidence,
    observation: ResumeTickObservation, policy: TransitionPolicy, *,
    authenticated_admission_digest: str,
    core_requirement: CoreVerificationRequirement,
    core_verification: CoreVerificationReceipt,
    core_report: CoreRehearsalReport,
) -> ResumeTickResult:
    """Recover durable state, admit exact evidence, perform at most one tick, return.

    authenticated_admission_digest must come from the trusted host admission
    boundary, never from the untrusted event body. This offline core does not
    implement webhook authentication or grant provider activation authority.
    """
    _digest(authenticated_admission_digest)
    if authenticated_admission_digest != event.digest:
        raise TriggerAdmissionError('event was not independently admitted')
    if (event.source,event.event_kind)!=(contract.source,contract.event_kind):
        raise TriggerAdmissionError('trigger source/kind mismatch')
    if (observation.portfolio_id,observation.policy_digest,observation.event)!=(contract.portfolio_id,contract.policy_digest,contract.transition_event) or policy.digest!=contract.policy_digest:
        raise TriggerAdmissionError('trigger contract mismatch')
    if event.observation_digest!=observation.digest:
        raise TriggerAdmissionError('observation substitution')
    if not core_report.all_passed or core_report.core_verification_receipt_digest!=core_verification.digest or core_report.candidate_revision!=core_verification.target_revision:
        raise TriggerAdmissionError('CORE-1 gate closed')
    if (core_verification.target_revision,core_verification.suite_ref,core_verification.verifier_ref)!=(core_requirement.required_revision,core_requirement.required_suite_ref,core_requirement.required_verifier_ref) or core_verification.test_count<core_requirement.minimum_test_count:
        raise TriggerAdmissionError('verification gate mismatch')
    # Event evidence cannot itself grant transition authority.
    if observation.authority_grant is not None:
        raise TriggerAdmissionError('trigger cannot carry authority grant')
    bound = replace(observation, canonical_refs=tuple(sorted(set(observation.canonical_refs+(event.admission_ref,'trigger:'+event.digest)))))
    store=SqlitePortfolioHeadStore(database)
    state,_,recovery=recover_portfolio_after_restart(store,contract.portfolio_id)
    # Persist the exact event->observation binding before calling the existing CAS
    # runtime. A crash before/after its commit can safely redeliver the same event.
    with sqlite3.connect(database,timeout=30) as connection:
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('CREATE TABLE IF NOT EXISTS external_trigger_bindings (identity TEXT PRIMARY KEY, admission_digest TEXT NOT NULL, observation_digest TEXT NOT NULL)')
        connection.execute('BEGIN IMMEDIATE')
        old=connection.execute('SELECT admission_digest,observation_digest FROM external_trigger_bindings WHERE identity=?',(event.identity,)).fetchone()
        expected=(event.digest,bound.digest)
        if old is not None and old!=expected:
            raise TriggerAdmissionError('event identity reused with different evidence')
        connection.execute('INSERT OR IGNORE INTO external_trigger_bindings VALUES (?,?,?)',(event.identity,*expected))
    # Check historical checkpoints, not just the latest, for delayed redelivery.
    with sqlite3.connect(database) as connection:
        rows=connection.execute('SELECT checkpoint_json FROM portfolio_checkpoints WHERE portfolio_id=? ORDER BY generation',(contract.portfolio_id,)).fetchall()
    for (encoded,) in rows:
        checkpoint=deserialize_checkpoint(encoded)
        if bound.checkpoint_ref in checkpoint.canonical_refs:
            return ResumeTickResult(portfolio_id=contract.portfolio_id,disposition='already_applied',observation_digest=bound.digest,pre_generation=state.generation,post_generation=state.generation,pre_state_digest=state.digest,post_state_digest=state.digest,checkpoint_digest=checkpoint.digest,recovery_report_digest=recovery.digest)
    return resume_tick(store,contract.portfolio_id,policy,bound,core_requirement=core_requirement,core_verification=core_verification)
