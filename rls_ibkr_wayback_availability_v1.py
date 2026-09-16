#!/usr/bin/env python3
import hashlib
import json
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKER_VERSION='RLS-IBKR-WAYBACK-AVAILABILITY-v1'
AUTHORITY='OBSERVATION_ONLY_NO_RLS_ADMISSION_AUTHORITY'
TARGETS=[
    {'id':'GOFILE_2019','url':'https://gofile.io/?c=gRd3kH','timestamp':'20190828'},
    {'id':'COMMUNITY_ZIP_HTTP_2021','url':'http://potential-investments.com/ib_shorting.zip','timestamp':'20210412'},
    {'id':'COMMUNITY_ZIP_HTTPS_2021','url':'https://potential-investments.com/ib_shorting.zip','timestamp':'20210412'},
]
OUT=Path('workloads/artifacts/rls_ibkr_wayback_availability_v1.json')
UA='RLS-Build-Colony-Wayback-Availability/1.0'

def query(t):
    q=urllib.parse.urlencode({'url':t['url'],'timestamp':t['timestamp']})
    endpoint='https://archive.org/wayback/available?'+q
    try:
        req=urllib.request.Request(endpoint,headers={'User-Agent':UA,'Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read()
            obj=json.loads(raw)
        closest=(obj.get('archived_snapshots') or {}).get('closest')
        return {
            'id':t['id'],'target_url':t['url'],'requested_timestamp':t['timestamp'],
            'endpoint_http_status':r.status,'response_sha256':hashlib.sha256(raw).hexdigest(),
            'available':bool(closest and closest.get('available')),
            'closest':None if not closest else {
                'available':closest.get('available'),
                'status':closest.get('status'),
                'timestamp':closest.get('timestamp'),
                'url':closest.get('url')
            },'error':None
        }
    except urllib.error.HTTPError as e:
        return {'id':t['id'],'target_url':t['url'],'requested_timestamp':t['timestamp'],'endpoint_http_status':e.code,'available':False,'closest':None,'error':f'HTTP {e.code}'}
    except Exception as e:
        return {'id':t['id'],'target_url':t['url'],'requested_timestamp':t['timestamp'],'endpoint_http_status':None,'available':False,'closest':None,'error':f'{type(e).__name__}: {e}'}

def main():
    rows=[query(t) for t in TARGETS]
    payload={
        'worker_version':WORKER_VERSION,
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'authority':AUTHORITY,
        'credential_policy':{'user_specific_credentials_used':False,'api_key_used':False,'account_login_used':False},
        'selection':'FIXED_TARGETS_AND_PUBLICATION_DATES_PREDECLARED',
        'results':rows,
        'archive_snapshot_bytes_opened':False,
        'historical_dataset_bytes_opened':False,
        'economic_values_opened':False,
        'admission_authority_granted':False
    }
    canonical=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    payload['evidence_digest_sha256']=hashlib.sha256(canonical).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    print('worker_version=',WORKER_VERSION)
    print('evidence_digest_sha256=',payload['evidence_digest_sha256'])
    for r in rows:
        print(r['id'], 'endpoint=',r['endpoint_http_status'],'available=',r['available'],'closest=',r['closest'],'error=',r['error'])
if __name__=='__main__': main()
