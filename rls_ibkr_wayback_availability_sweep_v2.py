#!/usr/bin/env python3
import concurrent.futures, hashlib, json, os, time, urllib.parse, urllib.request
from datetime import date

WORKER_VERSION='RLS-IBKR-WAYBACK-AVAILABILITY-SWEEP-WORKER-v2'
PROTOCOL='RLS-IBKR-WAYBACK-AVAILABILITY-SWEEP-v2'
AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'
TARGET='http://potential-investments.com/ib_shorting.zip'
ENDPOINT='https://archive.org/wayback/available'
TIMEOUT=12
MAX_ATTEMPTS=2
MAX_WORKERS=8
KNOWN='20260221140226'

def month_iter(y1,m1,y2,m2):
    y,m=y1,m1
    while (y,m)<=(y2,m2):
        yield y,m
        m+=1
        if m==13: y+=1; m=1

def anchors():
    out=[]
    for y,m in month_iter(2019,8,2026,8):
        for d in (1,15): out.append(f'{y:04d}{m:02d}{d:02d}')
    assert len(out)==170
    return out

def query(anchor):
    q=urllib.parse.urlencode({'url':TARGET,'timestamp':anchor})
    url=f'{ENDPOINT}?{q}'
    last=None
    for attempt in range(1,MAX_ATTEMPTS+1):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'RLS-Build-Colony-WaybackSweep/2.0'})
            with urllib.request.urlopen(req,timeout=TIMEOUT) as r:
                raw=r.read(1024*1024)
                status=getattr(r,'status',r.getcode())
            obj=json.loads(raw.decode('utf-8'))
            closest=((obj.get('archived_snapshots') or {}).get('closest') or {})
            return {
              'anchor':anchor,'transport_status':'OK','http_status':status,'attempts':attempt,
              'available':bool(closest.get('available')),
              'snapshot_status':str(closest.get('status')) if closest.get('status') is not None else None,
              'snapshot_timestamp':closest.get('timestamp'),
              'snapshot_url':closest.get('url')
            }
        except Exception as exc:
            last=f'{type(exc).__name__}: {exc}'
            if attempt<MAX_ATTEMPTS: time.sleep(0.35*attempt)
    return {'anchor':anchor,'transport_status':'ERROR','attempts':MAX_ATTEMPTS,'error':last,'available':False,'snapshot_status':None,'snapshot_timestamp':None,'snapshot_url':None}

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def main():
    aa=anchors()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        rows=list(ex.map(query,aa))
    rows.sort(key=lambda r:r['anchor'])
    snaps={}
    for r in rows:
        ts=r.get('snapshot_timestamp'); u=r.get('snapshot_url')
        if r.get('available') and ts and u:
            snaps[(ts,u)]={'timestamp':ts,'url':u,'status':r.get('snapshot_status')}
    distinct=sorted(snaps.values(),key=lambda x:(x['timestamp'],x['url']))
    unresolved=[r['anchor'] for r in rows if r['transport_status']!='OK']
    no_snapshot=[r['anchor'] for r in rows if r['transport_status']=='OK' and not r['available']]
    new=[x for x in distinct if x['timestamp']!=KNOWN]
    result={
      'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,
      'target':TARGET,'anchor_rule':{'first_month':'2019-08','last_month':'2026-08','days_per_month':[1,15],'anchor_count':len(aa),'no_early_stop':True},
      'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},
      'archived_snapshot_bytes_opened':False,'economic_values_opened':False,'admission_authority_granted':False,
      'queries':rows,'observed_anchor_count':sum(r['transport_status']=='OK' for r in rows),
      'unresolved_anchor_count':len(unresolved),'unresolved_anchors':unresolved,
      'no_snapshot_anchor_count':len(no_snapshot),
      'distinct_snapshot_count':len(distinct),'distinct_snapshots':distinct,
      'new_distinct_snapshot_count':len(new),'new_distinct_snapshots':new,
      'known_already_inspected_snapshot':KNOWN
    }
    result['status']='COMPLETE' if not unresolved else 'INCOMPLETE_TRANSPORT'
    result['evidence_digest_sha256']=digest(dict(result))
    os.makedirs('workloads/artifacts',exist_ok=True)
    p='workloads/artifacts/rls_ibkr_wayback_availability_sweep_v2.json'
    with open(p,'w',encoding='utf-8') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    print('status=',result['status'])
    print('observed_anchor_count=',result['observed_anchor_count'])
    print('unresolved_anchor_count=',result['unresolved_anchor_count'])
    print('distinct_snapshot_count=',result['distinct_snapshot_count'])
    print('distinct_snapshots=',result['distinct_snapshots'])
    print('new_distinct_snapshot_count=',result['new_distinct_snapshot_count'])
    print('evidence_digest_sha256=',result['evidence_digest_sha256'])
if __name__=='__main__': main()
