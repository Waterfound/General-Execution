#!/usr/bin/env python3
import hashlib,json,os,re,urllib.request
WORKER_VERSION='RLS-IBKR-WAYBACK-RAW-SNAPSHOT-PREFLIGHT-WORKER-2025-06-18-v1'; PROTOCOL='RLS-IBKR-WAYBACK-RAW-SNAPSHOT-PREFLIGHT-2025-06-18-v1'; AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'; TARGET='https://web.archive.org/web/20250618090506id_/ftp://shortstock@ftp2.interactivebrokers.com/usa.txt'; MAX=25*1024*1024
REQ={'SYM','CON','ISIN','REBATERATE','FEERATE','AVAILABLE'}
def dig(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def main():
 out={'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,'target':TARGET,'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},'economic_row_values_parsed':False,'economic_values_emitted':False,'admission_authority_granted':False}
 try:
  req=urllib.request.Request(TARGET,headers={'User-Agent':'RLS-Build-Colony-RawPreflight/1.0','Accept-Encoding':'identity'})
  with urllib.request.urlopen(req,timeout=60) as r:
   out['http_status']=getattr(r,'status',r.getcode()); out['final_url']=r.geturl(); out['headers']={k.lower():v for k,v in r.headers.items() if k.lower() in {'content-type','content-length','content-location','last-modified','etag'}}; data=r.read(MAX+1)
  if len(data)>MAX: raise ValueError('BODY_EXCEEDS_25_MIB')
  out['byte_length']=len(data); out['sha256']=hashlib.sha256(data).hexdigest(); out['looks_like_html']=data.lstrip()[:64].lower().startswith((b'<!doctype html',b'<html'))
  lines=data.splitlines(); bof=[x for x in lines if x.startswith(b'#BOF')]; hdr=[x for x in lines if x.startswith(b'#SYM')]; eof=[x for x in lines if x.startswith(b'#EOF')]; out['marker_counts']={'BOF':len(bof),'SYM':len(hdr),'EOF':len(eof)}
  if len(bof)!=1 or len(hdr)!=1 or len(eof)!=1: raise ValueError('STRUCTURAL_MARKER_COUNT_FAIL')
  bof_s=bof[0].decode('utf-8','strict').strip(); hdr_s=hdr[0].decode('utf-8','strict').strip(); eof_s=eof[0].decode('utf-8','strict').strip(); bp=bof_s.split('|'); out['bof_marker']=bof_s; out['bof_date']=bp[1] if len(bp)>1 else None; out['bof_time']=bp[2] if len(bp)>2 else None
  cols=[c for c in hdr_s.lstrip('#').split('|') if c!='']; out['header_columns']=cols; out['required_fields_present']={c:(c in cols) for c in sorted(REQ)}
  ep=eof_s.split('|'); declared=None
  for x in ep[1:]:
   if x.strip().isdigit(): declared=int(x.strip()); break
  out['eof_declared_row_count']=declared; physical=sum(1 for x in lines if x and not x.startswith(b'#')); out['physical_data_row_count']=physical; out['row_count_match']=(declared is None or declared==physical)
  out['bof_month_match']=(out['bof_date']=='2025.06.18'); out['required_fields_all_present']=all(out['required_fields_present'].values())
  out['snapshot_preflight_pass']=bool(len(data)>0 and not out['looks_like_html'] and out['bof_month_match'] and out['required_fields_all_present'] and out['row_count_match'] and '20250618090506' in out.get('final_url',''))
  out['status']='PREFLIGHT_PASS_SINGLE_PIT_SNAPSHOT_ONLY' if out['snapshot_preflight_pass'] else 'PREFLIGHT_FAIL'
 except Exception as e: out['status']='PREFLIGHT_FAIL'; out['error']=f'{type(e).__name__}: {e}'
 out['evidence_digest_sha256']=dig(dict(out)); os.makedirs('workloads/artifacts',exist_ok=True); json.dump(out,open('workloads/artifacts/rls_ibkr_wayback_raw_snapshot_preflight_2025_06_18_v1.json','w'),indent=2,sort_keys=True)
 print('status=',out['status']); print('http_status=',out.get('http_status')); print('final_url=',out.get('final_url')); print('byte_length=',out.get('byte_length')); print('sha256=',out.get('sha256')); print('bof_date=',out.get('bof_date')); print('bof_time=',out.get('bof_time')); print('header_columns=',out.get('header_columns')); print('physical_data_row_count=',out.get('physical_data_row_count')); print('eof_declared_row_count=',out.get('eof_declared_row_count')); print('evidence_digest_sha256=',out['evidence_digest_sha256'])
if __name__=='__main__':main()
