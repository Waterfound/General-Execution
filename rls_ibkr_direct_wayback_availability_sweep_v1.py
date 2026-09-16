#!/usr/bin/env python3
import concurrent.futures, hashlib, json, os, time, urllib.parse, urllib.request

WORKER_VERSION='RLS-IBKR-DIRECT-WAYBACK-AVAILABILITY-SWEEP-WORKER-v1'
PROTOCOL='RLS-IBKR-DIRECT-WAYBACK-AVAILABILITY-SWEEP-v1'
AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'
ENDPOINT='https://archive.org/wayback/available'
TARGETS=['http://ftp2.interactivebrokers.com/usa.txt','https://ftp2.interactivebrokers.com/usa.txt','http://ftp3.interactivebrokers.com/usa.txt','https://ftp3.interactivebrokers.com/usa.txt']

def months(a,b):
    y,m=map(int,a.split('-')); yy,mm=map(int,b.split('-')); out=[]
    while (y,m)<=(yy,mm):
        out.append(f'{y:04d}-{m:02d}'); m+=1
        if m==13: y+=1; m=1
    return out
MISSING=months('2016-09','2017-09')+months('2024-07','2026-08')
QUERIES=[(t,m,d,f'{m.replace("-","")}{d:02d}') for t in TARGETS for m in MISSING for d in (1,15)]

def query(item):
    target,month,day,anchor=item; url=ENDPOINT+'?'+urllib.parse.urlencode({'url':target,'timestamp':anchor}); last=None
    for attempt in range(1,4):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'RLS-Build-Colony-DirectIBKRWayback/1.0'})
            with urllib.request.urlopen(req,timeout=15) as r:
                raw=r.read(1024*1024); status=getattr(r,'status',r.getcode())
            o=json.loads(raw.decode('utf-8')); c=((o.get('archived_snapshots') or {}).get('closest') or {})
            return {'target':target,'missing_month':month,'anchor':anchor,'transport_status':'OK','http_status':status,'attempts':attempt,'available':bool(c.get('available')),'snapshot_status':str(c.get('status')) if c.get('status') is not None else None,'snapshot_timestamp':c.get('timestamp'),'snapshot_url':c.get('url')}
        except Exception as exc:
            last=f'{type(exc).__name__}: {exc}'
            if attempt<3: time.sleep((0.75,2.0)[attempt-1])
    return {'target':target,'missing_month':month,'anchor':anchor,'transport_status':'ERROR','attempts':3,'available':False,'snapshot_status':None,'snapshot_timestamp':None,'snapshot_url':None,'error':last}

def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def main():
    assert len(MISSING)==39 and len(QUERIES)==312
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(query,QUERIES))
    rows.sort(key=lambda r:(r['target'],r['anchor']))
    snaps={}
    for r in rows:
        if r.get('available') and r.get('snapshot_timestamp') and r.get('snapshot_url'):
            key=(r['target'],r['snapshot_timestamp'],r['snapshot_url']); snaps[key]={'target':r['target'],'timestamp':r['snapshot_timestamp'],'url':r['snapshot_url'],'status':r.get('snapshot_status')}
    distinct=sorted(snaps.values(),key=lambda x:(x['target'],x['timestamp'],x['url']))
    for s in distinct:
        ts=s['timestamp']; s['snapshot_month']=f'{ts[:4]}-{ts[4:6]}' if isinstance(ts,str) and len(ts)>=6 else None; s['snapshot_month_is_currently_missing']=s['snapshot_month'] in set(MISSING)
    unresolved=[{'target':r['target'],'anchor':r['anchor']} for r in rows if r['transport_status']!='OK']
    candidates=[s for s in distinct if s['snapshot_month_is_currently_missing']]
    result={'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,'targets':TARGETS,'missing_months':MISSING,'query_count':312,'observed_query_count':312-len(unresolved),'unresolved_query_count':len(unresolved),'unresolved_queries':unresolved,'distinct_snapshot_count':len(distinct),'distinct_snapshots':distinct,'missing_month_snapshot_candidate_count':len(candidates),'missing_month_snapshot_candidates':candidates,'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},'archived_snapshot_bytes_opened':False,'economic_values_opened':False,'admission_authority_granted':False}
    result['status']='COMPLETE' if not unresolved else 'INCOMPLETE_TRANSPORT'; result['evidence_digest_sha256']=digest(dict(result))
    os.makedirs('workloads/artifacts',exist_ok=True)
    with open('workloads/artifacts/rls_ibkr_direct_wayback_availability_sweep_v1.json','w') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    print('status=',result['status']); print('observed_query_count=',result['observed_query_count']); print('unresolved_query_count=',result['unresolved_query_count']); print('distinct_snapshot_count=',result['distinct_snapshot_count']); print('missing_month_snapshot_candidate_count=',result['missing_month_snapshot_candidate_count']); print('missing_month_snapshot_candidates=',result['missing_month_snapshot_candidates']); print('evidence_digest_sha256=',result['evidence_digest_sha256'])
if __name__=='__main__': main()
