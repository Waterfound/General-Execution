"""Strict offline cross-source geographic-ID reconciliation for public Austin permits.

The only verified output is a public property *reference*: no ownership, contact,
beneficial identity, market opportunity, customer, or valuation is inferred.
Inputs are compact public source observations gathered by a connector; not original
HTTP response bytes. This tool does not crawl sources or use private owner data.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import re
from pathlib import Path

DATASET = '3syk-w9eu'
GIS_LAYER = 'TCAD_public/MapServer/0'
ID = re.compile(r'[0-9]{10}\Z')
PERMIT = re.compile(r'[0-9]{4}-[0-9]{6} [A-Z]{1,4}\Z')
ZIP = re.compile(r'[0-9]{5}(?:-[0-9]{4})?\Z')


class EvidenceError(ValueError):
    pass


def _dict(v, label):
    if not isinstance(v, dict):
        raise EvidenceError(f'{label}: object required')
    return v


def _list(v, label, maximum=100):
    if not isinstance(v, list) or not 0 < len(v) <= maximum:
        raise EvidenceError(f'{label}: nonempty bounded array required')
    return v


def _text(v, label, maximum=150):
    if not isinstance(v, str) or not v.strip() or len(v) > maximum:
        raise EvidenceError(f'{label}: string missing or invalid')
    return v.strip()


def _id(v, label):
    value = _text(v, label)
    if not ID.fullmatch(value):
        raise EvidenceError(f'{label}: ten-digit string Geographic ID required; never coerce to int')
    return value


def _zip(v, label):
    if v is None or v == '':
        return None
    value = _text(v, label)
    if not ZIP.fullmatch(value):
        raise EvidenceError(f'{label}: invalid postal code')
    return value[:5]


def _source(metadata):
    meta = _dict(metadata, 'provenance')
    if meta.get('evidence_class') != 'CONNECTOR_EXTRACTED_PUBLIC_JSON_NOT_RAW_BYTES':
        raise EvidenceError('provenance: no authenticated raw-byte claim')
    if meta.get('austin_dataset') != DATASET or meta.get('gis_layer') != GIS_LAYER:
        raise EvidenceError('untrusted source binding')
    if meta.get('complete_sample') is not True or meta.get('gis_complete') is not True:
        raise EvidenceError('incomplete pagination or source response')
    if not isinstance(meta.get('gis_counts'), dict):
        raise EvidenceError('missing independently checked GIS cardinalities')
    for label in ('austin_url', 'gis_url'):
        url = _text(meta.get(label), label, 1000)
        if label == 'austin_url':
            if not url.startswith('https://data.austintexas.gov/resource/3syk-w9eu.json?'):
                raise EvidenceError('unauthorized Austin URL')
        elif not url.startswith('https://gis.traviscountytx.gov/server1/rest/services/Boundaries_and_Jurisdictions/TCAD_public/MapServer/0/query?'):
            raise EvidenceError('unauthorized GIS URL')
    return meta


def reconcile(snapshot):
    data = _dict(snapshot, 'snapshot')
    if data.get('schema') != 'wrm.cr001.official-permit-property.v1':
        raise EvidenceError('unknown schema')
    meta = _source(data.get('provenance'))
    permits = _list(data.get('permits'), 'permits')
    parcels = _list(data.get('parcels'), 'parcels')
    seen_permits = set()
    ids = Counter()
    for row in permits:
        r = _dict(row, 'permit')
        num = _text(r.get('permit_number'), 'permit_number')
        if not PERMIT.fullmatch(num):
            raise EvidenceError('permit_number: invalid or noncanonical')
        if num in seen_permits:
            raise EvidenceError('duplicate permit id')
        seen_permits.add(num)
        geo = _id(r.get('tcad_id'), 'tcad_id')
        ids[geo] += 1
        _zip(r.get('original_zip'), 'original_zip')
        # timestamp is publisher floating local date, not verified timezone
        stamp = _text(r.get('issue_date'), 'issue_date')
        try:
            datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError as e:
            raise EvidenceError('issue_date: invalid floating datetime') from e
        _text(r.get('jurisdiction'), 'jurisdiction')
    parcel_by_geo = {}
    for entry in parcels:
        p = _dict(entry, 'parcel')
        geo = _id(p.get('geo_id'), 'geo_id')
        if geo not in ids:
            raise EvidenceError('GIS parcel outside bounded permit sample')
        if type(p.get('PROP_ID')) is not int or p['PROP_ID'] <= 0:
            raise EvidenceError('invalid Property ID')
        _zip(p.get('situs_zip'), 'situs_zip')
        if p.get('situs_address') is not None:
            _text(p['situs_address'], 'situs_address')
        parcel_by_geo.setdefault(geo, []).append(p)
    observed_counts=meta['gis_counts']
    if set(observed_counts) != set(ids):
        raise EvidenceError('GIS count queries do not cover full sample')
    for geo in ids:
        n=observed_counts[geo]
        if type(n) is not int or n < 0 or n > 100:
            raise EvidenceError('invalid independently observed cardinality')
        if n != len(parcel_by_geo.get(geo, [])):
            raise EvidenceError('GIS completeness mismatch; fail closed')
    out = []
    for r in permits:
        found = parcel_by_geo.get(r['tcad_id'], [])
        if not found:
            outcome,prop = 'NOT_FOUND_IN_BOUNDED_GIS_QUERY',None
        elif len(found) != 1:
            outcome,prop = 'AMBIGUOUS_GIS_GEOGRAPHIC_ID',None
        else:
            p = found[0]
            rz,pz = _zip(r.get('original_zip'),'original_zip'),_zip(p.get('situs_zip'),'situs_zip')
            if rz and pz and rz != pz:
                outcome,prop = 'POSTAL_CODE_CONFLICT_REVIEW',None
            elif rz is None or pz is None:
                outcome,prop = 'ZIP_EVIDENCE_INCOMPLETE_REVIEW',None
            else:
                outcome,prop = 'MATCHED_GEOGRAPHIC_REFERENCE',p['PROP_ID']
        out.append({
            'permit_number':r['permit_number'],'geographic_id':r['tcad_id'],
            'outcome':outcome,'public_property_reference':prop,
            'owner_identity_verified':False,'property_legal_identity_verified':False,
            'commercial_value_verified':False,
            'source_austin':meta['austin_url'], 'source_gis':meta['gis_url']
        })
    counts=Counter(row['outcome'] for row in out)
    return {
        'schema':'wrm.cr001.permit-property-report.v1',
        'provenance_class':meta['evidence_class'],
        'sample_size':len(out),'distinct_geo_ids':len(ids),
        'geographic_reference_match_count':counts.get('MATCHED_GEOGRAPHIC_REFERENCE',0),
        'outcome_counts':dict(sorted(counts.items())),
        'rows':out,
        'limitations':['No original provider HTTP bytes available: sample is connector-extracted JSON',
                       'Matching publisher Geographic IDs and ZIP does NOT establish legal ownership, parcel-unit identity, or lead quality',
                       'Dates are publisher floating timestamps, not independently timezone-validated',
                       'No customer, competitive advantage, WTP, revenue, or unattended operation proven']
    }


def canonical_digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source',type=Path)
    args=ap.parse_args()
    source=json.loads(args.source.read_text(encoding='utf-8'))
    result=reconcile(source)
    result['normalized_snapshot_sha256']=canonical_digest(source)
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=='__main__':main()
