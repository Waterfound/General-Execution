#!/usr/bin/env python3
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import hashlib,json,os,re,urllib.request

PROTOCOL='RLS-IBKR-WAYBACK-SNAPSHOT-SEMANTIC-VALIDATION-2025-06-18-v1.1'
AUTHORITY='OBSERVATION_ONLY_RECOVERY_PRECHECK_NO_ADMISSION_AUTHORITY'
URL='https://web.archive.org/web/20250618090506id_/ftp://shortstock@ftp2.interactivebrokers.com/usa.txt'
EXPECTED_SHA='74d6bd14aeadcddc74fa5a00c597a6b36ad50bdaa953fec90525c1a351b9c553'
EXPECTED_HEADER='#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|'
EXPECTED_ROWS=17613
NUM=re.compile(r'^[+-]?\d+(?:\.\d+)?$'); INT=re.compile(r'^\d+$'); LB=re.compile(r'^>(\d+)$')

def numeric_or_blank(s,label):
 s=s.strip()
 if not s:return None
 if not NUM.fullmatch(s):raise ValueError(f'{label}: undocumented numeric literal')
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
 req=urllib.request.Request(URL,headers={'User-Agent':'RLS-Build-Colony-SemanticValidation/1.1'})
 with urllib.request.urlopen(req,timeout=90) as r:raw=r.read()
 source_sha=sha256(raw).hexdigest()
 if source_sha!=EXPECTED_SHA:raise SystemExit(f'FAIL source sha mismatch {source_sha}')
 text=raw.decode('utf-8-sig',errors='strict');lines=text.splitlines()
 while lines and not lines[0].strip():lines.pop(0)
 while lines and not lines[-1].strip():lines.pop()
 if len(lines)<3:raise SystemExit('FAIL snapshot too short')
 if lines[0] != '#BOF|2025.06.18|04:54:55':raise SystemExit('FAIL BOF mismatch')
 if lines[1] != EXPECTED_HEADER:raise SystemExit('FAIL header mismatch')
 m=re.fullmatch(r'#EOF\|(\d+)\|?',lines[-1])
 if not m:raise SystemExit('FAIL EOF shape')
 body=lines[2:-1]
 if int(m.group(1))!=EXPECTED_ROWS or len(body)!=EXPECTED_ROWS:raise SystemExit('FAIL row count')
 seen=set();paired=0;obs_avail=0;obs_unavail=0;missing_avail=0;missing_fee=0;figi_nonblank=0
 norm_hasher=hashlib.sha256()
 for i,line in enumerate(body,1):
  p=line.split('|')
  if len(p)!=10 or p[-1]!='':raise SystemExit(f'FAIL row {i} field count')
  sym,cur,name,con_s,isin,rebate,fee,avail,figi,_=p
  if not sym.strip() or not cur.strip():raise SystemExit(f'FAIL row {i} empty symbol/currency')
  if not INT.fullmatch(con_s.strip()) or int(con_s)<=0:raise SystemExit(f'FAIL row {i} CON')
  con=int(con_s)
  if con in seen:raise SystemExit(f'FAIL duplicate CON at row {i}')
  seen.add(con)
  numeric_or_blank(rebate,f'row {i} REBATERATE'); fee_n=numeric_or_blank(fee,f'row {i} FEERATE'); av=availability(avail,f'row {i} AVAILABLE')
  if av in ('OBSERVED_AVAILABLE','OBSERVED_AVAILABLE_LOWER_BOUND') and fee_n is None:raise SystemExit(f'FAIL row {i} positive AVAILABLE without FEERATE')
  if fee_n is None:missing_fee+=1
  if av=='MISSING':missing_avail+=1
  elif av=='OBSERVED_UNAVAILABLE':obs_unavail+=1
  else:obs_avail+=1
  if fee_n is not None and av!='MISSING':paired+=1
  if figi.strip():figi_nonblank+=1
  norm_hasher.update(line.encode('utf-8'));norm_hasher.update(b'\n')
 out={
  'protocol':PROTOCOL,'authority':AUTHORITY,'status':'VALID_SNAPSHOT_RECOVERY_PRECHECK_PASS' if paired>=1 else 'VALID_SNAPSHOT_RECOVERY_PRECHECK_FAIL',
  'source_sha256':source_sha,'snapshot_date':'2025-06-18','snapshot_time':'04:54:55','monthly_anchor_day':18,'row_count':len(body),'distinct_contract_count':len(seen),
  'paired_fee_availability_row_count':paired,'observed_available_row_count':obs_avail,'observed_unavailable_row_count':obs_unavail,'missing_availability_row_count':missing_avail,'missing_fee_row_count':missing_fee,'nonblank_figi_row_count':figi_nonblank,
  'normalized_body_sha256':norm_hasher.hexdigest(),'recovery_precheck_pass':paired>=1,
  'raw_rows_emitted':False,'identifiers_emitted':False,'economic_values_emitted':False,'strategy_outcomes_opened':False,'admission_authority_granted':False,'confirmation':'SEALED','capital_authorization':'0.00%'
 }
 out['evidence_digest_sha256']=digest(dict(out));os.makedirs('workloads/artifacts',exist_ok=True);json.dump(out,open('workloads/artifacts/rls_ibkr_wayback_snapshot_semantic_validation_2025_06_18_v1_1.json','w'),indent=2,sort_keys=True)
 for k in ('status','source_sha256','row_count','distinct_contract_count','paired_fee_availability_row_count','observed_available_row_count','observed_unavailable_row_count','missing_availability_row_count','missing_fee_row_count','nonblank_figi_row_count','recovery_precheck_pass','normalized_body_sha256','evidence_digest_sha256'):print(k,'=',out[k])
if __name__=='__main__':main()
