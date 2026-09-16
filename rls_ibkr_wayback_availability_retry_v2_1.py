#!/usr/bin/env python3
import concurrent.futures, hashlib, json, os, time, urllib.parse, urllib.request

WORKER_VERSION='RLS-IBKR-WAYBACK-AVAILABILITY-RETRY-WORKER-v2.1'
PROTOCOL='RLS-IBKR-WAYBACK-AVAILABILITY-RETRY-v2.1'
AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'
TARGET='http://potential-investments.com/ib_shorting.zip'
ENDPOINT='https://archive.org/wayback/available'
ANCHORS=['20231001','20231015','20231101','20231115','20231201','20231215','20240101','20240115','20240201','20240215','20240301','20240315','20240401','20240415','20240501','20240515','20240601','20240615','20240701','20240715','20240801','20240815','20240901','20240915','20241001','20241015','20241101','20241115','20241201','20241215','20250101','20250115','20250201','20250215','20250301','20250315','20250401','20250415','20250501','20250515','20250601','20250615','20250701','20250715','20250801','20250815','20250901','20250915','20251001','20251015','20251101','20251115','20251201','20251215','20260101','20260115','20260201','20260215','20260301','20260315','20260401','20260415','20260501','20260515','20260601','20260615','20260701','20260715','20260801','20260815']
BACKOFF=[0.75,2.0,4.0]

def query(anchor):
    url=ENDPOINT+'?'+urllib.parse.urlencode({'url':TARGET,'timestamp':anchor})
    last=None
    for attempt in range(1,5):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'RLS-Build-Colony-WaybackRetry/2.1'})
            with urllib.request.urlopen(req,timeout=20) as r:
                raw=r.read(1024*1024); status=getattr(r,'status',r.getcode())
            obj=json.loads(raw.decode('utf-8'))
            c=((obj.get('archived_snapshots') or {}).get('closest') or {})
            return {'anchor':anchor,'transport_status':'OK','http_status':status,'attempts':attempt,'available':bool(c.get('available')),'snapshot_status':str(c.get('status')) if c.get('status') is not None else None,'snapshot_timestamp':c.get('timestamp'),'snapshot_url':c.get('url')}
        except Exception as exc:
            last=f'{type(exc).__name__}: {exc}'
            if attempt<4: time.sleep(BACKOFF[attempt-1])
    return {'anchor':anchor,'transport_status':'ERROR','attempts':4,'available':False,'snapshot_status':None,'snapshot_timestamp':None,'snapshot_url':None,'error':last}

def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def main():
    assert len(ANCHORS)==70 and len(set(ANCHORS))==70
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: rows=list(ex.map(query,ANCHORS))
    rows.sort(key=lambda r:r['anchor'])
    snaps={}
    for r in rows:
        if r.get('available') and r.get('snapshot_timestamp') and r.get('snapshot_url'):
            snaps[(r['snapshot_timestamp'],r['snapshot_url'])]={'timestamp':r['snapshot_timestamp'],'url':r['snapshot_url'],'status':r.get('snapshot_status')}
    distinct=sorted(snaps.values(),key=lambda x:(x['timestamp'],x['url']))
    unresolved=[r['anchor'] for r in rows if r['transport_status']!='OK']
    result={'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,'target':TARGET,'input_anchor_count':70,'queries':rows,'observed_anchor_count':70-len(unresolved),'unresolved_anchor_count':len(unresolved),'unresolved_anchors':unresolved,'distinct_snapshot_count':len(distinct),'distinct_snapshots':distinct,'new_distinct_snapshots':[s for s in distinct if s['timestamp']!='20260221140226'],'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},'snapshot_bytes_opened':False,'economic_values_opened':False,'admission_authority_granted':False}
    result['status']='COMPLETE' if not unresolved else 'INCOMPLETE_TRANSPORT'
    result['evidence_digest_sha256']=digest(dict(result))
    os.makedirs('workloads/artifacts',exist_ok=True)
    with open('workloads/artifacts/rls_ibkr_wayback_availability_retry_v2_1.json','w') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    print('status=',result['status']); print('observed_anchor_count=',result['observed_anchor_count']); print('unresolved_anchor_count=',result['unresolved_anchor_count']); print('distinct_snapshots=',distinct); print('new_distinct_snapshots=',result['new_distinct_snapshots']); print('evidence_digest_sha256=',result['evidence_digest_sha256'])
if __name__=='__main__': main()
