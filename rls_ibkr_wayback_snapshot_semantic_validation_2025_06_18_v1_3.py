#!/usr/bin/env python3
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import hashlib,json,os,re,urllib.request
PROTOCOL='RLS-IBKR-WAYBACK-SNAPSHOT-SEMANTIC-VALIDATION-2025-06-18-v1.3'; AUTHORITY='OBSERVATION_ONLY_RECOVERY_PRECHECK_NO_ADMISSION_AUTHORITY'; URL='https://web.archive.org/web/20250618090506id_/ftp://shortstock@ftp2.interactivebrokers.com/usa.txt'; EXPECTED_SHA='74d6bd14aeadcddc74fa5a00c597a6b36ad50bdaa953fec90525c1a351b9c553'; EXPECTED_HEADER='#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|'; EXPECTED_ROWS=17613
NUM=re.compile(r'^[+-]?\d+(?:\.\d+)?$'); INT=re.compile(r'^\d+$'); LB=re.compile(r'^>(\d+)$'); MISSING={'','NA'}
def rate(s,label):
 s=s.strip()
 if s in MISSING:return None
 if not NUM.fullmatch(s):raise ValueError(f'{label}: undocumented literal')
 try:d=Decimal(s)
 except InvalidOperation as e:raise ValueError(f'{label}: invalid decimal') from e
 if not d.is_finite():raise ValueError(f'{label}: non-finite')
 return str(d.normalize())
def availability(s,label):
 s=s.strip()
 if not s:return 'MISSING'
 m=LB.fullmatch(s)
 if m:
  if int(m.group(1))<=0:raise ValueError(f'{label}: nonpositive lower bound')
  return 'OBSERVED_AVAILABLE_LOWER_BOUND'
 if INT.fullmatch(s):return 'OBSERVED_UNAVAILABLE' if int(s)==0 else 'OBSERVED_AVAILABLE'
 raise ValueError(f'{label}: undocumented literal')
def digest(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def main():
 req=urllib.request.Request(URL,headers={'User-Agent':'RLS-Build-Colony-SemanticValidation/1.3'})
 with urllib.request.urlopen(req,timeout=90) as r:raw=r.read()
 source_sha=sha256(raw).hexdigest();
 if source_sha!=EXPECTED_SHA:raise SystemExit('FAIL source sha mismatch')
 lines=raw.decode('utf-8-sig',errors='strict').splitlines()
 while lines and not lines[0].strip():lines.pop(0)
 while lines and not lines[-1].strip():lines.pop()
 if lines[0]!='#BOF|2025.06.18|04:54:55' or lines[1]!=EXPECTED_HEADER:raise SystemExit('FAIL envelope/header mismatch')
 m=re.fullmatch(r'#EOF\|(\d+)\|?',lines[-1]);body=lines[2:-1]
 if not m or int(m.group(1))!=EXPECTED_ROWS or len(body)!=EXPECTED_ROWS:raise SystemExit('FAIL row count')
 seen=set();paired=obs_avail=obs_unavail=missing_avail=missing_fee=missing_rebate=na_fee=na_rebate=figi_nonblank=avail_with_missing_fee=0; norm=hashlib.sha256()
 for i,line in enumerate(body,1):
  p=line.split('|')
  if len(p)!=10 or p[-1]!='':raise SystemExit(f'FAIL row {i} field count')
  sym,cur,name,con_s,isin,rebate,fee,avail,figi,_=p
  if not sym.strip() or not cur.strip():raise SystemExit(f'FAIL row {i} symbol/currency')
  if not INT.fullmatch(con_s.strip()) or int(con_s)<=0:raise SystemExit(f'FAIL row {i} CON')
  con=int(con_s)
  if con in seen:raise SystemExit(f'FAIL duplicate CON row {i}')
  seen.add(con); rp=rate(rebate,f'row {i} REBATERATE'); fp=rate(fee,f'row {i} FEERATE'); av=availability(avail,f'row {i} AVAILABLE')
  if rebate.strip()=='NA':na_rebate+=1
  if fee.strip()=='NA':na_fee+=1
  if rp is None:missing_rebate+=1
  if fp is None:missing_fee+=1
  if av=='MISSING':missing_avail+=1
  elif av=='OBSERVED_UNAVAILABLE':obs_unavail+=1
  else:obs_avail+=1
  if fp is not None and av!='MISSING':paired+=1
  if fp is None and av in ('OBSERVED_AVAILABLE','OBSERVED_AVAILABLE_LOWER_BOUND'):avail_with_missing_fee+=1
  if figi.strip():figi_nonblank+=1
  norm.update(line.encode());norm.update(b'\n')
 out={'protocol':PROTOCOL,'authority':AUTHORITY,'status':'VALID_MODERN_SNAPSHOT_RECOVERY_PRECHECK_PASS','source_sha256':source_sha,'snapshot_date':'2025-06-18','snapshot_time':'04:54:55','row_count':len(body),'distinct_contract_count':len(seen),'paired_fee_availability_row_count':paired,'observed_available_row_count':obs_avail,'observed_unavailable_row_count':obs_unavail,'missing_availability_row_count':missing_avail,'missing_fee_row_count':missing_fee,'missing_rebate_row_count':missing_rebate,'availability_with_missing_fee_row_count':avail_with_missing_fee,'na_fee_row_count':na_fee,'na_rebate_row_count':na_rebate,'nonblank_figi_row_count':figi_nonblank,'na_coerced_to_zero':False,'cross_field_imputation_used':False,'normalized_body_sha256':norm.hexdigest(),'recovery_precheck_pass':True,'raw_rows_emitted':False,'identifiers_emitted':False,'economic_values_emitted':False,'strategy_outcomes_opened':False,'admission_authority_granted':False,'confirmation':'SEALED','capital_authorization':'0.00%'};out['evidence_digest_sha256']=digest(dict(out));os.makedirs('workloads/artifacts',exist_ok=True);json.dump(out,open('workloads/artifacts/rls_ibkr_wayback_snapshot_semantic_validation_2025_06_18_v1_3.json','w'),indent=2,sort_keys=True)
 for k in ('status','row_count','distinct_contract_count','paired_fee_availability_row_count','missing_fee_row_count','availability_with_missing_fee_row_count','na_fee_row_count','na_rebate_row_count','nonblank_figi_row_count','recovery_precheck_pass','evidence_digest_sha256'):print(k,'=',out[k])
if __name__=='__main__':main()
