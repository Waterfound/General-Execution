"""Offline Thin Envelope requests. Selection and diagnosis never grant authority."""
from __future__ import annotations

from dataclasses import dataclass

from .canonical import sha256_digest
from .external_trigger import _digest
from .portfolio_persistence import recover_portfolio_after_restart, SqlitePortfolioHeadStore
from .resume_tick import ResumeTickResult


class EscalationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ThinEscalationEnvelope:
    target_system: str
    operation: str
    portfolio_id: str
    generation: int
    state_digest: str
    checkpoint_digest: str
    source_revision: str
    tick_digest: str
    evidence_digest: str
    requested_action_ref: str
    authority_created: bool = False
    repair_authorized: bool = False
    transport_authorized: bool = False

    def __post_init__(self):
        if (self.target_system,self.operation) not in {('build_colony','select_work'),('di','diagnose')}:
            raise EscalationError('unsupported system/operation')
        if any(value is not False for value in (self.authority_created,self.repair_authorized,self.transport_authorized)):
            raise EscalationError('envelope cannot grant authority')
        if type(self.generation) is not int or self.generation<0:
            raise EscalationError('invalid generation')
        for value in (self.state_digest,self.checkpoint_digest,self.tick_digest,self.evidence_digest): _digest(value)
        for value in (self.portfolio_id,self.source_revision,self.requested_action_ref):
            if not isinstance(value,str) or not value.strip(): raise EscalationError('missing provenance')

    @property
    def digest(self): return sha256_digest(self)


def prepare_escalation(database, portfolio_id: str, tick: ResumeTickResult, *, target_system: str, evidence_digest: str) -> ThinEscalationEnvelope:
    state,checkpoint,_=recover_portfolio_after_restart(SqlitePortfolioHeadStore(database),portfolio_id)
    if tick.portfolio_id!=portfolio_id or tick.post_state_digest!=state.digest or tick.post_generation!=state.generation or checkpoint is None:
        raise EscalationError('stale or missing durable provenance')
    if state.active.state=='human_gate' or checkpoint.authority_stop:
        raise EscalationError('human authority gate cannot escalate automatically')
    if target_system=='di' and state.active.state=='di_required': operation='diagnose'
    elif target_system=='build_colony' and tick.disposition=='external_input_required' and not tick.human_required: operation='select_work'
    else: raise EscalationError('no policy-authorized escalation at this frontier')
    return ThinEscalationEnvelope(target_system,operation,portfolio_id,state.generation,state.digest,checkpoint.digest,state.active.source_revision,tick.digest,evidence_digest,state.active.next_action_ref)


@dataclass(frozen=True, slots=True)
class EscalationResponse:
    request_digest: str
    responder: str
    evidence_digest: str
    available: bool
    advisory_ref: str | None = None
    repair_authorized: bool = False

    def __post_init__(self):
        _digest(self.request_digest); _digest(self.evidence_digest)
        if type(self.available) is not bool or self.repair_authorized is not False:
            raise EscalationError('response cannot grant repair authority')
        if self.available and (not isinstance(self.advisory_ref,str) or not self.advisory_ref.strip()):
            raise EscalationError('available response needs advisory evidence')

    @property
    def digest(self): return sha256_digest(self)


def admit_escalation_response(request: ThinEscalationEnvelope, response: EscalationResponse, *, authenticated_response_digest: str) -> str:
    if authenticated_response_digest!=response.digest or response.request_digest!=request.digest or response.responder!=request.target_system:
        raise EscalationError('response provenance mismatch')
    # This pure admission function cannot apply work selection, repair, or a tick.
    return 'advisory_only' if response.available else 'waiting_external'
