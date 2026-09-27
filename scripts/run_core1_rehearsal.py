#!/usr/bin/env python3
"""Bounded CORE-1 rehearsal. No provider calls, triggers, or runtime authority."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone

from general_execution import *
from general_execution.canonical import sha256_digest
from general_execution.vercel_sandbox import SandboxCommandEvidence, VercelSandboxConformanceRun

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = '04a47cd7031b608368de15ec2c99ccc715eb6cbf'


def encode(x):
    return json.loads(canonical_json(x))


def write(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(encode(x), sort_keys=True, indent=2) + '\n')


def fixtures():
    # Reuse only frozen input constructors; no fabricated test receipt is loaded.
    spec = importlib.util.spec_from_file_location('asp_inputs', ROOT/'tests/test_asp_transition.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admit(path):
    data = json.loads(path.read_text())
    values = dict(data['run'])
    values['command_evidence'] = tuple(SandboxCommandEvidence(**dict(c, args=tuple(c['args']))) for c in values['command_evidence'])
    run = VercelSandboxConformanceRun(**values)
    spec = VercelSandboxConformanceSpec(**data['spec'])
    manifest = CoreVerificationManifest(**data['manifest'])
    receipt = admit_vercel_core_verification(manifest, spec, run, executed_at=data['executed_at'])
    assert manifest.target_revision == CANDIDATE
    assert run.digest == data['run_digest'] and spec.digest == data['spec_digest']
    assert receipt.digest == data['receipt_digest'] and manifest.digest == data['manifest_digest']
    return manifest.requirement(), receipt


def ev(kind):
    return CheckpointEvidence(kind=kind, locator='fixture://core1/'+kind, digest=sha256_digest({'fixture':'core1-v1','kind':kind}))


def obs(state, policy, event='execution_started', kinds=('dispatch_admitted',), **kwargs):
    return ResumeTickObservation(portfolio_id=state.portfolio_id, expected_generation=state.generation,
        expected_state_digest=state.digest, policy_digest=policy.digest, event=event,
        evidence=tuple(ev(k) for k in kinds), action_ref='rehearsal://'+event,
        observed_at='2026-09-27T02:35:44.588899+00:00', summary='Bounded CORE-1 fixture '+event,
        canonical_refs=('fixture://rehearsals/core1-v1.json',), **kwargs)


def worker(mode, out, artifact):
    f = fixtures(); p = f.policy(); gate, receipt = admit(artifact)
    db = out/'cold.db'
    if mode == 'cold-init':
        state=f.portfolio(); store=SqlitePortfolioHeadStore(db); store.initialize(state)
        observation=obs(state,p)
        tick=resume_tick(store,state.portfolio_id,p,observation,core_requirement=gate,core_verification=receipt)
        assert tick.disposition=='committed' and tick.post_generation==1
        write(out/'cold-init.json',dict(pid=os.getpid(),tick=encode(tick),observation=encode(observation)))
        del store
    else:
        store=SqlitePortfolioHeadStore(db)
        state, checkpoint, report=recover_portfolio_after_restart(store,'durable-asp')
        prior=json.loads((out/'cold-init.json').read_text())
        assert os.getpid()!=prior['pid']
        assert state.digest==prior['tick']['post_state_digest']
        assert checkpoint.digest==prior['tick']['checkpoint_digest']
        assert state.generation==1 and state.active.state=='running'
        assert not report.fabricated_state and not report.fabricated_checkpoint
        assert 'core-verification:'+receipt.digest in checkpoint.canonical_refs
        write(out/'cold-recovered.json',dict(pid=os.getpid(),initiator_pid=prior['pid'],state=encode(state),checkpoint=encode(checkpoint),recovery=encode(report)))


def main(out, artifact):
    assert not out.exists(), 'Refusing to overwrite rehearsal evidence'
    out.mkdir(parents=True)
    gate,receipt=admit(artifact)
    f=fixtures(); p=f.policy()
    fixture=json.loads((ROOT/'rehearsals/core1-v1.json').read_text())
    assert fixture['verification_gate']['target_revision']==CANDIDATE
    # Verify every imported product source file against immutable Git candidate.
    files=subprocess.check_output(['git','ls-tree','-r','--name-only',CANDIDATE,'src','tests/test_asp_transition.py'],cwd=ROOT,text=True).splitlines()
    for path in files:
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',CANDIDATE+':'+path],cwd=ROOT),path
    proofs={}
    def prove(ids,name,value):
        path=out/(name+'.json'); write(path,value)
        digest=sha256_digest(value)
        for key in ids: proofs.setdefault(key,[]).append((str(path.relative_to(ROOT)),digest))
    for mode in ('cold-init','cold-recover'):
        subprocess.run([sys.executable,__file__,'--worker',mode,'--output',str(out),'--artifact',str(artifact)],check=True,cwd=ROOT)
    prove(('cold_resume','checkpoint_reconstruction','no_chat_dependency'),'cold-resume-proof',
        {'initiator':json.loads((out/'cold-init.json').read_text()),'recovered':json.loads((out/'cold-recovered.json').read_text()),'source_files_verified':len(files)})

    # Concurrent duplicate observations both reach commit; SQLite CAS chooses one winner.
    state=f.portfolio(); db=out/'race.db'; SqlitePortfolioHeadStore(db).initialize(state)
    barrier=threading.Barrier(2)
    class RaceStore(SqlitePortfolioHeadStore):
        def commit(self,*args,**kwargs):
            barrier.wait(timeout=15)
            return super().commit(*args,**kwargs)
    observation=obs(state,p)
    def race(_):
        return resume_tick(RaceStore(db),state.portfolio_id,p,observation,core_requirement=gate,core_verification=receipt)
    with ThreadPoolExecutor(max_workers=2) as pool: ticks=list(pool.map(race,range(2)))
    assert sorted(t.disposition for t in ticks)==['already_applied','committed']
    store=SqlitePortfolioHeadStore(db); current,_=store.load(state.portfolio_id)
    assert current.generation==1
    stale=obs(state,p,'authority_required',('authority_boundary_reached',))
    stale_result=resume_tick(store,state.portfolio_id,p,stale,core_requirement=gate,core_verification=receipt)
    after,_=store.load(state.portfolio_id)
    assert stale_result.disposition=='stale_observation' and current==after
    prove(('duplicate_tick_idempotent','stale_write_rejected'),'race-and-stale',{'ticks':[encode(t) for t in ticks],'stale':encode(stale_result),'state':encode(after)})

    for name,start,event,kinds in [('promotion','verifying','verification_passed',('verifier_pass',)),('parking','waiting_external','external_blocker',('external_blocker','no_internal_work'))]:
        state=f.portfolio(start,passive=(f.passive('PASSIVE-A'),f.passive('PASSIVE-B')))
        admission=admit_passive_wake(state,p,'PASSIVE-A',(ev('wake_condition_satisfied'),))
        store=SqlitePortfolioHeadStore(out/(name+'.db')); store.initialize(state)
        tick=resume_tick(store,state.portfolio_id,p,obs(state,p,event,kinds,wake_admission=admission),core_requirement=gate,core_verification=receipt)
        current,_=store.load(state.portfolio_id); checkpoint=store.latest_checkpoint(state.portfolio_id)
        assert tick.disposition=='committed'
        assert current.active.work_id=='SECONDARY' and current.active.state=='ready'
        assert current.secondary.work_id=='PASSIVE-A' and current.secondary.state=='ready'
        assert current.active.authority_ref is None and current.secondary.authority_ref is None
        ids=['passive_wake_admission','no_hidden_authority']
        if name=='promotion':
            assert tuple(x.work_id for x in current.passive)==('PASSIVE-B',)
            assert checkpoint.state_after=='complete'
            try:
                apply_active_transition(state,p,event,(ev('verifier_pass'),),action_ref='rehearsal://forbidden-selection',observed_at='2026-09-27T00:00:00Z',summary='negative fixture',canonical_refs=('fixture://core1',),replacement_secondary=f.secondary('EXTERNAL'))
            except AspTransitionError as exc:
                assert 'external replacement selection is not authorized' in str(exc)
            else: raise AssertionError('external replacement accepted')
            ids+=['verified_secondary_promotion']
        else:
            parked={x.work_id:x for x in current.passive}['ACTIVE']
            assert parked.wake_condition==state.active.wake_condition and parked.blockers==state.active.blockers
            assert parked.state=='passive'
            ids+=['external_blocker_parking']
        prove(ids,name,{'before':encode(state),'wake':encode(admission),'tick':encode(tick),'after':encode(current),'checkpoint':encode(checkpoint)})

    rp=RetryPolicy(policy_id='core1-bounded-retry',revision='1',authority_ref='fixture://core1/retry-simulation-only',authority_digest=sha256_digest(fixture['scenarios'][3]),network_retry_limit=2,throttle_retry_limit=3,throttle_initial_backoff_seconds=5,throttle_max_backoff_seconds=12,unknown_reproduction_limit=1)
    def decision(kind,**kw):
        return decide_retry(rp,FailureObservation(failure_class=kind,failure_code='fixture.'+kind,evidence_digest=sha256_digest({'fixture':kind}),**kw))
    network=[decision('network_timeout',automatic_retry_count=i) for i in range(3)]
    throttle=[decision('provider_throttled',automatic_retry_count=i) for i in range(4)]
    deterministic=decision('deterministic_assertion')
    unknown=[decision('unknown_failure',independent_reproduction_count=i) for i in range(2)]
    boundaries=[decision(k,boundary_detail='fixture boundary') for k in ('cost_boundary','security_boundary','authority_boundary')]
    assert [x.disposition for x in network]==['retry','retry','diagnose']
    assert [x.delay_seconds for x in throttle]==[5,10,12,0] and throttle[-1].disposition=='diagnose'
    assert deterministic.disposition=='diagnose' and not deterministic.automatic_retry_authorized
    assert [x.disposition for x in unknown]==['independent_reproduction','diagnose']
    assert unknown[0].independent_reproduction_authorized and not unknown[1].independent_reproduction_authorized
    assert [x.disposition for x in boundaries]==['stop','human_gate','human_gate']
    assert all(x.authority_ref is None and not x.automatic_retry_authorized and not x.transport_authority for x in boundaries)
    assert all(x.human_required for x in boundaries[1:])
    prove(('bounded_retry','unknown_failure_single_reproduction','cost_security_authority_stop'),'retry-boundaries',{'policy':encode(rp),'network':[encode(x) for x in network],'throttle':[encode(x) for x in throttle],'deterministic':encode(deterministic),'unknown':[encode(x) for x in unknown],'boundaries':[encode(x) for x in boundaries]})

    state=f.portfolio('running'); store=SqlitePortfolioHeadStore(out/'human.db'); store.initialize(state)
    tick=resume_tick(store,state.portfolio_id,p,obs(state,p,'authority_required',('authority_boundary_reached',)),core_requirement=gate,core_verification=receipt)
    request=resume_tick(SqlitePortfolioHeadStore(out/'human.db'),state.portfolio_id,p,None,core_requirement=gate,core_verification=receipt)
    current,_=store.load(state.portfolio_id); checkpoint=store.latest_checkpoint(state.portfolio_id)
    assert tick.disposition=='committed' and current.active.state=='human_gate'
    assert current.active.authority_ref is None and checkpoint.authority_stop and checkpoint.next_transition_refs==()
    assert request.human_required and request.requested_action_ref=='authority://human-decision'
    prove(('human_gate_stop','no_hidden_authority'),'human-stop',{'tick':encode(tick),'request':encode(request),'state':encode(current),'checkpoint':encode(checkpoint)})

    assert set(proofs)==set(fixture['required_assertions'])
    assertions=tuple(CoreRehearsalAssertion(assertion_id=k,passed=True,evidence_refs=tuple(sorted(set(x[0] for x in v))),evidence_digests=tuple(sorted(set(x[1] for x in v)))) for k,v in sorted(proofs.items()))
    report=build_core_rehearsal_report(CANDIDATE,receipt.digest,assertions)
    assert report.all_passed and len(report.assertions)==13
    write(out/'core1-receipt.json',report)
    write(out/'evidence-ledger.json',{'schema_version':'ge.core1-evidence-ledger.v1','executed_at':datetime.now(timezone.utc).isoformat(),'candidate_revision':CANDIDATE,'verification_receipt_digest':receipt.digest,'report_digest':report.digest,'assertions':{a.assertion_id:encode(a) for a in assertions},'provider_invoked':False,'unattended_runtime_enabled':False})
    print(json.dumps({'status':'PASS','assertions':13,'report_digest':report.digest}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--artifact',type=Path,required=True); parser.add_argument('--worker',choices=('cold-init','cold-recover'))
    args=parser.parse_args()
    if args.worker: worker(args.worker,args.output.resolve(),args.artifact.resolve())
    else: main(args.output.resolve(),args.artifact.resolve())
