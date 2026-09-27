import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from general_execution import *
from general_execution.external_trigger import ExternalTriggerEvidence, TriggerContract, TriggerAdmissionError, consume_external_trigger
from general_execution.thin_envelope_escalation import EscalationError, EscalationResponse, admit_escalation_response, prepare_escalation
from test_asp_transition import portfolio, policy

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/durable-execution/2026-09-27'


def gate():
    artifact=json.loads((EVIDENCE/'wave5-original.json').read_text())
    receipt=CoreVerificationReceipt(**artifact['receipt'])
    report=json.loads((EVIDENCE/'core1-run-002/core1-receipt.json').read_text())
    report['assertions']=tuple(CoreRehearsalAssertion(**dict(a,evidence_refs=tuple(a['evidence_refs']),evidence_digests=tuple(a['evidence_digests']))) for a in report['assertions'])
    return dict(core_requirement=CoreVerificationManifest(**artifact['manifest']).requirement(),core_verification=receipt,core_report=CoreRehearsalReport(**report))


def setup(db, state_name='ready', event='execution_started', evidence_kind='dispatch_admitted'):
    state=portfolio(state_name); p=policy(); SqlitePortfolioHeadStore(db).initialize(state)
    observation=ResumeTickObservation(portfolio_id=state.portfolio_id,expected_generation=0,expected_state_digest=state.digest,policy_digest=p.digest,event=event,evidence=(CheckpointEvidence(kind=evidence_kind,locator='fixture://wave8',digest=sha256_digest({'kind':evidence_kind})),),action_ref='fixture://wave8',observed_at='2026-09-27T00:00:00Z',summary='Offline trigger fixture',canonical_refs=('fixture://wave8',))
    evidence=ExternalTriggerEvidence('fixture-provider','event-1','observation-ready',sha256_digest({'payload':'one'}),observation.digest,'admission://offline-fixture')
    contract=TriggerContract(evidence.source,evidence.event_kind,state.portfolio_id,p.digest,event)
    return contract,evidence,observation,p


def invoke(db, values, **changes):
    c,e,o,p=values; kwargs=gate(); kwargs.update(changes)
    return consume_external_trigger(db,c,e,o,p,authenticated_admission_digest=e.digest,**kwargs)


def test_one_tick_and_delayed_duplicate_after_newer_checkpoint(tmp_path):
    db=tmp_path/'state.db'; values=setup(db)
    first=invoke(db,values); assert first.disposition=='committed' and first.post_generation==1
    state,_=SqlitePortfolioHeadStore(db).load('durable-asp'); c,e,o,p=values
    newer=replace(o,expected_generation=1,expected_state_digest=state.digest,event='authority_required',evidence=(CheckpointEvidence(kind='authority_boundary_reached',locator='fixture://boundary',digest=sha256_digest('boundary')),))
    gate_values=gate(); gate_values.pop('core_report')
    result=resume_tick(SqlitePortfolioHeadStore(db),'durable-asp',p,newer,**gate_values)
    assert result.post_generation==2
    replay=invoke(db,values)
    assert replay.disposition=='already_applied' and replay.post_generation==2
    assert replay.checkpoint_digest==first.checkpoint_digest


@pytest.mark.parametrize('field,value',[('source','other'),('event_kind','other'),('observation_digest','sha256:'+'0'*64)])
def test_substitution_rejected_without_state_change(tmp_path,field,value):
    db=tmp_path/'state.db'; c,e,o,p=setup(db)
    with pytest.raises(TriggerAdmissionError): invoke(db,(c,replace(e,**{field:value}),o,p))
    assert SqlitePortfolioHeadStore(db).load('durable-asp')[0].generation==0


def test_untrusted_event_digest_is_not_accepted(tmp_path):
    db=tmp_path/'state.db'; c,e,o,p=setup(db)
    with pytest.raises(TriggerAdmissionError,match='independently admitted'):
        consume_external_trigger(db,c,e,o,p,authenticated_admission_digest=sha256_digest('wrong'),**gate())


def test_event_identity_collision_rejected(tmp_path):
    db=tmp_path/'state.db'; values=setup(db); invoke(db,values); c,e,o,p=values
    with pytest.raises(TriggerAdmissionError,match='identity reused'):
        invoke(db,(c,replace(e,payload_digest=sha256_digest('different')),o,p))


def test_concurrent_invocations_commit_once(tmp_path):
    db=tmp_path/'state.db'; values=setup(db)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:invoke(db,values),range(2)))
    assert sorted(r.disposition for r in results)==['already_applied','committed']
    assert SqlitePortfolioHeadStore(db).load('durable-asp')[0].generation==1


def test_missed_delivery_recovers_from_new_process(tmp_path):
    db=tmp_path/'state.db'; values=setup(db)
    # New process reconstructs the same admitted observation from durable artifacts.
    code="""
import sys
from pathlib import Path
from test_wave8_adapters import setup, invoke
from general_execution import SqlitePortfolioHeadStore
db=Path(sys.argv[1]); fixture=Path(sys.argv[2]); values=setup(fixture)
r=invoke(db,values)
assert r.disposition=='committed' and r.post_generation==1
"""
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT/'tests'))
    subprocess.run([sys.executable,'-c',code,str(db),str(tmp_path/'fixture.db')],env=env,check=True)
    assert invoke(db,values).disposition=='already_applied'


def test_crash_before_tick_redelivery(tmp_path,monkeypatch):
    import general_execution.external_trigger as module
    db=tmp_path/'state.db'; values=setup(db); original=module.resume_tick
    def crash(*a,**kw): raise RuntimeError('simulated crash before tick')
    monkeypatch.setattr(module,'resume_tick',crash)
    with pytest.raises(RuntimeError): invoke(db,values)
    monkeypatch.setattr(module,'resume_tick',original)
    assert invoke(db,values).disposition=='committed'


def test_crash_after_commit_redelivery(tmp_path,monkeypatch):
    import general_execution.external_trigger as module
    db=tmp_path/'state.db'; values=setup(db); original=module.resume_tick
    def crash(*a,**kw): original(*a,**kw); raise RuntimeError('simulated crash after commit')
    monkeypatch.setattr(module,'resume_tick',crash)
    with pytest.raises(RuntimeError): invoke(db,values)
    monkeypatch.setattr(module,'resume_tick',original)
    assert invoke(db,values).disposition=='already_applied'


def test_core_gate_mismatch_rejected(tmp_path):
    db=tmp_path/'state.db'; values=setup(db); g=gate()
    with pytest.raises(TriggerAdmissionError): invoke(db,values,core_requirement=replace(g['core_requirement'],required_revision='1'*40))
    with pytest.raises(TriggerAdmissionError): invoke(db,values,core_report=replace(g['core_report'],core_verification_receipt_digest=sha256_digest('other')))


def test_stale_event_cannot_advance_head(tmp_path):
    db=tmp_path/'state.db'; values=setup(db); invoke(db,values); c,e,o,p=values
    new_o=replace(o,summary='different observation'); new_e=replace(e,event_id='event-2',observation_digest=new_o.digest)
    assert invoke(db,(c,new_e,new_o,p)).disposition=='stale_observation'


def test_di_provenance_unavailable_and_no_repair(tmp_path):
    db=tmp_path/'state.db'; values=setup(db,'running','diagnosis_required','failure_evidence'); tick=invoke(db,values)
    envelope=prepare_escalation(db,'durable-asp',tick,target_system='di',evidence_digest=sha256_digest('failure'))
    assert envelope.operation=='diagnose' and not envelope.repair_authorized and not envelope.transport_authorized
    response=EscalationResponse(envelope.digest,'di',sha256_digest('unavailable'),False)
    assert admit_escalation_response(envelope,response,authenticated_response_digest=response.digest)=='waiting_external'
    available=replace(response,available=True,advisory_ref='artifact://diagnosis')
    assert admit_escalation_response(envelope,available,authenticated_response_digest=available.digest)=='advisory_only'
    with pytest.raises(EscalationError): replace(available,repair_authorized=True)
    with pytest.raises(EscalationError): replace(envelope,transport_authorized=True)
    wrong=replace(response,responder='cii')
    with pytest.raises(EscalationError): admit_escalation_response(envelope,wrong,authenticated_response_digest=wrong.digest)
    assert SqlitePortfolioHeadStore(db).load('durable-asp')[0].generation==1


def test_build_colony_selection_is_advisory(tmp_path):
    db=tmp_path/'state.db'; values=setup(db); invoke(db,values); c,e,o,p=values; g=gate(); g.pop('core_report')
    tick=resume_tick(SqlitePortfolioHeadStore(db),'durable-asp',p,None,**g)
    request=prepare_escalation(db,'durable-asp',tick,target_system='build_colony',evidence_digest=e.digest)
    assert request.operation=='select_work' and not request.authority_created
    with pytest.raises(EscalationError): prepare_escalation(db,'durable-asp',replace(tick,post_state_digest=sha256_digest('stale'),pre_state_digest=sha256_digest('stale')),target_system='build_colony',evidence_digest=e.digest)


def test_human_gate_cannot_auto_escalate(tmp_path):
    db=tmp_path/'state.db'; values=setup(db,'running','authority_required','authority_boundary_reached'); tick=invoke(db,values)
    with pytest.raises(EscalationError,match='human authority gate'):
        prepare_escalation(db,'durable-asp',tick,target_system='di',evidence_digest=values[1].digest)
