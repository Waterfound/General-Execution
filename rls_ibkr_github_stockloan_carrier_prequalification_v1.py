#!/usr/bin/env python3
import csv, hashlib, io, json, os, urllib.request
from datetime import datetime

WORKER_VERSION='RLS-IBKR-GITHUB-STOCKLOAN-CARRIER-PREQUALIFICATION-WORKER-v1'
PROTOCOL='RLS-IBKR-GITHUB-STOCKLOAN-CARRIER-PREQUALIFICATION-v1'
AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'
REPO='lbelt567/TradingData'
COMMIT='869ea1cee4e09a0ffaddbb77b56609a0e1c5bd8f'
PATH='data_upload/stock_loan_data.csv'
EXPECTED_GIT_BLOB='92822a1a2e3d2ec4023db95a47bede98c55df225'
EXPECTED_TREE_SIZE=1356565
URL=f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{PATH}'
TEMPORAL_NAMES={'timestamp','datetime','date','fetched_at','observed_at','bof_timestamp','time'}
CANONICAL=['SYM','CON','ISIN','FEERATE','REBATERATE','AVAILABLE']
MISSING_RECENT_START='2024-07'
MISSING_RECENT_END='2026-08'

def canonical_digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def git_blob_sha1(data):
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def parse_dt(s):
    s=(s or '').strip()
    if not s: return None
    candidates=[s, s.replace('Z','+00:00')]
    for v in candidates:
        try: return datetime.fromisoformat(v)
        except Exception: pass
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%Y.%m.%d %H:%M:%S','%m/%d/%Y %H:%M:%S','%m/%d/%Y'):
        try: return datetime.strptime(s,fmt)
        except Exception: pass
    return None

def main():
    result={
      'worker_version':WORKER_VERSION,'protocol':PROTOCOL,'authority':AUTHORITY,
      'candidate':{'repository':REPO,'commit':COMMIT,'path':PATH,'expected_git_blob_sha':EXPECTED_GIT_BLOB},
      'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},
      'economic_values_emitted':False,'admission_authority_granted':False,'strategy_outcomes_opened':False
    }
    req=urllib.request.Request(URL,headers={'User-Agent':'RLS-Build-Colony/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: data=r.read(EXPECTED_TREE_SIZE+1024)
        result['retrieval_status']='OK'
        result['byte_length']=len(data)
        result['sha256']=hashlib.sha256(data).hexdigest()
        result['computed_git_blob_sha']=git_blob_sha1(data)
        result['git_blob_match']=(result['computed_git_blob_sha']==EXPECTED_GIT_BLOB)
        result['tree_size_match']=(len(data)==EXPECTED_TREE_SIZE)
        text=data.decode('utf-8-sig','strict')
        reader=csv.DictReader(io.StringIO(text))
        header=reader.fieldnames or []
        result['header']=header
        lower={h.strip().lower():h for h in header if h is not None}
        temporal=[lower[n] for n in TEMPORAL_NAMES if n in lower]
        result['temporal_columns']=sorted(temporal)
        result['canonical_fields_present']={c:(c.lower() in lower) for c in CANONICAL}
        rows=0; temporal_nonempty=0; parsed=[]
        for row in reader:
            rows += 1
            row_had=False
            for col in temporal:
                val=row.get(col)
                if val is not None and str(val).strip():
                    temporal_nonempty += 1 if not row_had else 0
                    row_had=True
                    dt=parse_dt(str(val))
                    if dt is not None: parsed.append(dt)
                    break
        result['row_count']=rows
        result['rows_with_nonempty_temporal_value']=temporal_nonempty
        months=sorted(set(dt.strftime('%Y-%m') for dt in parsed))
        dates=sorted(set(dt.strftime('%Y-%m-%d') for dt in parsed))
        result['temporal_summary']={
          'parsed_temporal_value_count':len(parsed),
          'distinct_dates':len(dates),
          'earliest':min((dt.isoformat() for dt in parsed),default=None),
          'latest':max((dt.isoformat() for dt in parsed),default=None),
          'observed_months':months,
          'missing_window_months_observed':[m for m in months if MISSING_RECENT_START <= m <= MISSING_RECENT_END]
        }
        req_fields=result['canonical_fields_present']
        result['prequalification_pass']=bool(result['git_blob_match'] and result['tree_size_match'] and temporal and req_fields['SYM'] and req_fields['FEERATE'] and req_fields['AVAILABLE'] and result['temporal_summary']['missing_window_months_observed'])
        result['status']='PREQUALIFICATION_PASS' if result['prequalification_pass'] else 'PREQUALIFICATION_FAIL'
    except Exception as exc:
        result['retrieval_status']='ERROR'; result['status']='PREQUALIFICATION_FAIL'; result['error']=f'{type(exc).__name__}: {exc}'
    basis=dict(result); result['evidence_digest_sha256']=canonical_digest(basis)
    os.makedirs('workloads/artifacts',exist_ok=True)
    out='workloads/artifacts/rls_ibkr_github_stockloan_carrier_prequalification_v1.json'
    with open(out,'w',encoding='utf-8') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    print('status=',result.get('status'))
    print('git_blob_match=',result.get('git_blob_match'))
    print('header=',result.get('header'))
    print('temporal_columns=',result.get('temporal_columns'))
    print('canonical_fields_present=',result.get('canonical_fields_present'))
    print('row_count=',result.get('row_count'))
    print('temporal_summary=',result.get('temporal_summary'))
    print('evidence_digest_sha256=',result['evidence_digest_sha256'])
if __name__=='__main__': main()
