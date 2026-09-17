#!/usr/bin/env python3
import hashlib,json,os,time,urllib.parse,urllib.request
WORKER_VERSION='RLS-IBKR-SHORTSTOCK-PATH-WAYBACK-RETRY-WORKER-v1.2'; PROTOCOL='RLS-IBKR-SHORTSTOCK-PATH-WAYBACK-RETRY-v1.2'; AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'; ENDPOINT='https://archive.org/wayback/available'
PAIRS=[
('http://www.interactivebrokers.com/shortstock/usa.txt','20170801'),('http://www.interactivebrokers.com/shortstock/usa.txt','20170815'),('http://www.interactivebrokers.com/shortstock/usa.txt','20170901'),('http://www.interactivebrokers.com/shortstock/usa.txt','20170915'),('http://www.interactivebrokers.com/shortstock/usa.txt','20240701'),('http://www.interactivebrokers.com/shortstock/usa.txt','20240715'),('http://www.interactivebrokers.com/shortstock/usa.txt','20240801'),('http://www.interactivebrokers.com/shortstock/usa.txt','20240815'),('http://www.interactivebrokers.com/shortstock/usa.txt','20240901'),('http://www.interactivebrokers.com/shortstock/usa.txt','20240915'),('https://www.interactivebrokers.com/shortstock/usa.txt','20170115')]
def q(p):
 t,a=p;u=ENDPOINT+'?'+urllib.parse.urlencode({'url':t,'timestamp':a});last=None
 for attempt in range(1,6):
  try:
   req=urllib.request.Request(u,headers={'User-Agent':'RLS-Build-Colony-ShortstockRetry/1.2'})
   with urllib.request.urlopen(req,timeout=25) as r: raw=r.read(1024*1024); hs=getattr(r,'status',r.getcode())
   o=json.loads(raw.decode());c=((o.get('archived_snapshots') or {}).get('closest') or {})
   return {'target':t,'anchor':a,'transport_status':'OK','http_status':hs,'attempts':attempt,'available':bool(c.get('available')),'snapshot_status':str(c.get('status')) if c.get('status') is not None else None,'snapshot_timestamp':c.get('timestamp'),'snapshot_url':c.get('url')}
  except Exception as e:
   last=f'{type(e).__name__}: {e}'
   if attempt<5: time.sleep((1,3,7,12)[attempt-1])
 return {'target':t,'anchor':a,'transport_status':'ERROR','attempts':5,'available':False,'snapshot_status':None,'snapshot_timestamp':None,'snapshot_url':None,'error':last}
def dig(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def main():
 assert len(PAIRS)==11 and len(set(PAIRS))==11
 rows=[q(p) for p in PAIRS]; rows.sort(key=lambda r:(r['target'],r['anchor'])); snaps={}
 for r in rows:
  if r.get('available') and r.get('snapshot_timestamp') and r.get('snapshot_url'): snaps[(r['target'],r['snapshot_timestamp'],r['snapshot_url'])]={'target':r['target'],'timestamp':r['snapshot_timestamp'],'url':r['snapshot_url'],'status':r.get('snapshot_status')}
 ds=sorted(snaps.values(),key=lambda x:(x['target'],x['timestamp'],x['url'])); missing=set(['2017-08','2017-09','2024-07','2024-08','2024-09'])
 for s in ds:
  ts=s['timestamp'];s['snapshot_month']=f'{ts[:4]}-{ts[4:6]}' if isinstance(ts,str) and len(ts)>=6 else None;s['snapshot_month_is_currently_missing']=s['snapshot_month'] in missing
 unr=[{'target':r['target'],'anchor':r['anchor']} for r in rows if r['transport_status']!='OK'];cand=[s for s in ds if s['snapshot_month_is_currently_missing']]
 out={'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,'query_count':11,'observed_query_count':11-len(unr),'unresolved_query_count':len(unr),'unresolved_queries':unr,'queries':rows,'distinct_snapshot_count':len(ds),'distinct_snapshots':ds,'missing_month_snapshot_candidate_count':len(cand),'missing_month_snapshot_candidates':cand,'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},'snapshot_bytes_opened':False,'economic_values_opened':False,'admission_authority_granted':False}; out['status']='COMPLETE' if not unr else 'TRANSPORT_BOUNDARY_CONFIRMED'; out['evidence_digest_sha256']=dig(dict(out)); os.makedirs('workloads/artifacts',exist_ok=True); json.dump(out,open('workloads/artifacts/rls_ibkr_shortstock_path_wayback_retry_v1_2.json','w'),indent=2,sort_keys=True)
 print('status=',out['status']);print('observed_query_count=',out['observed_query_count']);print('unresolved_query_count=',out['unresolved_query_count']);print('distinct_snapshots=',out['distinct_snapshots']);print('missing_month_snapshot_candidates=',out['missing_month_snapshot_candidates']);print('evidence_digest_sha256=',out['evidence_digest_sha256'])
if __name__=='__main__': main()
