#!/usr/bin/env python3
import concurrent.futures,hashlib,json,os,time,urllib.parse,urllib.request
WORKER_VERSION='RLS-IBKR-SHORTSTOCK-PATH-WAYBACK-RETRY-WORKER-v1.1'; PROTOCOL='RLS-IBKR-SHORTSTOCK-PATH-WAYBACK-RETRY-v1.1'; AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'; ENDPOINT='https://archive.org/wayback/available'
def months(a,b):
 y,m=map(int,a.split('-')); yy,mm=map(int,b.split('-')); o=[]
 while (y,m)<=(yy,mm):
  o.append(f'{y:04d}-{m:02d}');m+=1
  if m==13:y+=1;m=1
 return o
MISSING=months('2016-09','2017-09')+months('2024-07','2026-08'); ALL=[f'{m.replace("-","")}{d:02d}' for m in MISSING for d in (1,15)]; FTP2_HTTPS_MONTHS=['2017-08','2017-09']+months('2024-07','2026-08'); FTP2_HTTPS=[f'{m.replace("-","")}{d:02d}' for m in FTP2_HTTPS_MONTHS for d in (1,15)]
PAIRS=[]
for t in ('http://ftp3.interactivebrokers.com/shortstock/usa.txt','http://www.interactivebrokers.com/shortstock/usa.txt','https://ftp3.interactivebrokers.com/shortstock/usa.txt','https://www.interactivebrokers.com/shortstock/usa.txt'):
 PAIRS += [(t,a) for a in ALL]
PAIRS += [('https://ftp2.interactivebrokers.com/shortstock/usa.txt',a) for a in FTP2_HTTPS]
def q(p):
 t,a=p;u=ENDPOINT+'?'+urllib.parse.urlencode({'url':t,'timestamp':a});last=None
 for attempt in range(1,5):
  try:
   req=urllib.request.Request(u,headers={'User-Agent':'RLS-Build-Colony-ShortstockRetry/1.1'})
   with urllib.request.urlopen(req,timeout=20) as r:raw=r.read(1024*1024);hs=getattr(r,'status',r.getcode())
   o=json.loads(raw.decode());c=((o.get('archived_snapshots') or {}).get('closest') or {})
   return {'target':t,'anchor':a,'transport_status':'OK','http_status':hs,'attempts':attempt,'available':bool(c.get('available')),'snapshot_status':str(c.get('status')) if c.get('status') is not None else None,'snapshot_timestamp':c.get('timestamp'),'snapshot_url':c.get('url')}
  except Exception as e:
   last=f'{type(e).__name__}: {e}'
   if attempt<4:time.sleep((0.75,2.0,4.0)[attempt-1])
 return {'target':t,'anchor':a,'transport_status':'ERROR','attempts':4,'available':False,'snapshot_status':None,'snapshot_timestamp':None,'snapshot_url':None,'error':last}
def dig(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def main():
 assert len(PAIRS)==368 and len(set(PAIRS))==368
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:rows=list(ex.map(q,PAIRS))
 rows.sort(key=lambda r:(r['target'],r['anchor']));snaps={}
 for r in rows:
  if r.get('available') and r.get('snapshot_timestamp') and r.get('snapshot_url'):snaps[(r['target'],r['snapshot_timestamp'],r['snapshot_url'])]={'target':r['target'],'timestamp':r['snapshot_timestamp'],'url':r['snapshot_url'],'status':r.get('snapshot_status')}
 ds=sorted(snaps.values(),key=lambda x:(x['target'],x['timestamp'],x['url']));miss=set(MISSING)
 for s in ds:
  ts=s['timestamp'];s['snapshot_month']=f'{ts[:4]}-{ts[4:6]}' if isinstance(ts,str) and len(ts)>=6 else None;s['snapshot_month_is_currently_missing']=s['snapshot_month'] in miss
 unr=[{'target':r['target'],'anchor':r['anchor']} for r in rows if r['transport_status']!='OK'];cand=[s for s in ds if s['snapshot_month_is_currently_missing']]
 out={'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,'query_count':368,'observed_query_count':368-len(unr),'unresolved_query_count':len(unr),'unresolved_queries':unr,'queries':rows,'distinct_snapshot_count':len(ds),'distinct_snapshots':ds,'missing_month_snapshot_candidate_count':len(cand),'missing_month_snapshot_candidates':cand,'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},'snapshot_bytes_opened':False,'economic_values_opened':False,'admission_authority_granted':False};out['status']='COMPLETE' if not unr else 'INCOMPLETE_TRANSPORT';out['evidence_digest_sha256']=dig(dict(out));os.makedirs('workloads/artifacts',exist_ok=True);json.dump(out,open('workloads/artifacts/rls_ibkr_shortstock_path_wayback_retry_v1_1.json','w'),indent=2,sort_keys=True)
 print('status=',out['status']);print('observed_query_count=',out['observed_query_count']);print('unresolved_query_count=',out['unresolved_query_count']);print('distinct_snapshots=',out['distinct_snapshots']);print('missing_month_snapshot_candidates=',out['missing_month_snapshot_candidates']);print('evidence_digest_sha256=',out['evidence_digest_sha256'])
if __name__=='__main__':main()
