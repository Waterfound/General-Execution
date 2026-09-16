#!/usr/bin/env python3
import concurrent.futures,hashlib,json,os,time,urllib.parse,urllib.request
WORKER_VERSION='RLS-IBKR-WAYBACK-JUNE-2025-DAILY-DISCOVERY-WORKER-v1'; PROTOCOL='RLS-IBKR-WAYBACK-JUNE-2025-DAILY-DISCOVERY-v1'; AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'; TARGET='http://ftp2.interactivebrokers.com/usa.txt'; ENDPOINT='https://archive.org/wayback/available'; ANCHORS=[f'202506{d:02d}' for d in range(1,31)]
def q(a):
 u=ENDPOINT+'?'+urllib.parse.urlencode({'url':TARGET,'timestamp':a}); last=None
 for attempt in range(1,5):
  try:
   req=urllib.request.Request(u,headers={'User-Agent':'RLS-Build-Colony-June2025/1.0'})
   with urllib.request.urlopen(req,timeout=20) as r: raw=r.read(1024*1024); hs=getattr(r,'status',r.getcode())
   o=json.loads(raw.decode()); c=((o.get('archived_snapshots') or {}).get('closest') or {})
   return {'anchor':a,'transport_status':'OK','http_status':hs,'attempts':attempt,'available':bool(c.get('available')),'snapshot_status':str(c.get('status')) if c.get('status') is not None else None,'snapshot_timestamp':c.get('timestamp'),'snapshot_url':c.get('url')}
  except Exception as e:
   last=f'{type(e).__name__}: {e}'
   if attempt<4: time.sleep((0.75,2.0,4.0)[attempt-1])
 return {'anchor':a,'transport_status':'ERROR','attempts':4,'available':False,'snapshot_status':None,'snapshot_timestamp':None,'snapshot_url':None,'error':last}
def dig(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: rows=list(ex.map(q,ANCHORS))
 rows.sort(key=lambda r:r['anchor']); snaps={}
 for r in rows:
  if r.get('available') and r.get('snapshot_timestamp') and r.get('snapshot_url'):
   k=(r['snapshot_timestamp'],r['snapshot_url']); snaps[k]={'timestamp':r['snapshot_timestamp'],'url':r['snapshot_url'],'status':r.get('snapshot_status')}
 ds=sorted(snaps.values(),key=lambda x:(x['timestamp'],x['url'])); june=[s for s in ds if str(s['timestamp']).startswith('202506')]; dates=sorted(set(f"{s['timestamp'][:4]}-{s['timestamp'][4:6]}-{s['timestamp'][6:8]}" for s in june if len(str(s['timestamp']))>=8)); unr=[r['anchor'] for r in rows if r['transport_status']!='OK']
 out={'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,'target':TARGET,'anchor_count':30,'observed_anchor_count':30-len(unr),'unresolved_anchor_count':len(unr),'unresolved_anchors':unr,'queries':rows,'distinct_snapshot_count':len(ds),'distinct_snapshots':ds,'june_2025_snapshot_count':len(june),'june_2025_snapshots':june,'june_2025_distinct_snapshot_dates':dates,'june_2025_distinct_snapshot_date_count':len(dates),'archived_snapshot_bytes_opened':False,'economic_values_opened':False,'admission_authority_granted':False,'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False}}; out['status']='COMPLETE' if not unr else 'INCOMPLETE_TRANSPORT'; out['evidence_digest_sha256']=dig(dict(out)); os.makedirs('workloads/artifacts',exist_ok=True); json.dump(out,open('workloads/artifacts/rls_ibkr_wayback_june_2025_daily_discovery_v1.json','w'),indent=2,sort_keys=True)
 print('status=',out['status']); print('observed_anchor_count=',out['observed_anchor_count']); print('unresolved_anchor_count=',out['unresolved_anchor_count']); print('june_2025_distinct_snapshot_date_count=',out['june_2025_distinct_snapshot_date_count']); print('june_2025_distinct_snapshot_dates=',out['june_2025_distinct_snapshot_dates']); print('june_2025_snapshots=',out['june_2025_snapshots']); print('evidence_digest_sha256=',out['evidence_digest_sha256'])
if __name__=='__main__':main()
