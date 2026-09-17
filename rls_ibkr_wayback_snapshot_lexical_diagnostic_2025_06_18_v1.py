#!/usr/bin/env python3
import collections,hashlib,json,os,re,urllib.request
PROTOCOL='RLS-IBKR-WAYBACK-SNAPSHOT-LEXICAL-DIAGNOSTIC-2025-06-18-v1'; AUTHORITY='OBSERVATION_ONLY_FORMAT_DIAGNOSTIC_NO_ADMISSION_AUTHORITY'; URL='https://web.archive.org/web/20250618090506id_/ftp://shortstock@ftp2.interactivebrokers.com/usa.txt'; EXPECTED_SHA='74d6bd14aeadcddc74fa5a00c597a6b36ad50bdaa953fec90525c1a351b9c553'; NUM=re.compile(r'^[+-]?\d+(?:\.\d+)?$'); INT=re.compile(r'^\d+$'); LB=re.compile(r'^>\d+$')
def main():
 req=urllib.request.Request(URL,headers={'User-Agent':'RLS-Build-Colony-LexicalDiagnostic/1.0'})
 with urllib.request.urlopen(req,timeout=90) as r: raw=r.read()
 sha=hashlib.sha256(raw).hexdigest()
 if sha!=EXPECTED_SHA: raise SystemExit('FAIL source sha mismatch')
 lines=raw.decode('utf-8-sig',errors='strict').splitlines(); body=lines[2:-1]; c=collections.Counter()
 for line in body:
  p=line.split('|')
  if len(p)!=10 or p[-1]!='': continue
  for field,token,kind in [('REBATERATE',p[5].strip(),'num'),('FEERATE',p[6].strip(),'num'),('AVAILABLE',p[7].strip(),'avail')]:
   ok=(not token) or (NUM.fullmatch(token) is not None) if kind=='num' else ((not token) or INT.fullmatch(token) is not None or LB.fullmatch(token) is not None)
   if not ok: c[(field,token)]+=1
 items=[{'field':f,'literal':v,'count':n,'literal_sha256':hashlib.sha256(v.encode()).hexdigest()} for (f,v),n in sorted(c.items())]
 out={'protocol':PROTOCOL,'authority':AUTHORITY,'status':'COMPLETE','source_sha256':sha,'unsupported_token_kind_count':len(items),'unsupported_tokens':items,'raw_rows_emitted':False,'identifiers_emitted':False,'ordinary_numeric_values_emitted':False,'strategy_outcomes_opened':False,'admission_authority_granted':False,'confirmation':'SEALED','capital_authorization':'0.00%'}
 out['evidence_digest_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest(); os.makedirs('workloads/artifacts',exist_ok=True); json.dump(out,open('workloads/artifacts/rls_ibkr_wayback_snapshot_lexical_diagnostic_2025_06_18_v1.json','w'),indent=2,sort_keys=True)
 print('status=',out['status']); print('unsupported_token_kind_count=',len(items)); print('unsupported_token_total_count=',sum(x['count'] for x in items)); print('evidence_digest_sha256=',out['evidence_digest_sha256'])
if __name__=='__main__': main()
