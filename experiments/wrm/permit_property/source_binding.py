"""Fail-closed URL lineage contract for the bounded Austin–Travis sample.

This validates declared *query lineage*, not HTTP response authenticity. No network,
raw provider bytes, legal title, or commercial equivalence is established.
"""
from urllib.parse import parse_qsl, urlsplit

AUSTIN_HOST = 'data.austintexas.gov'
AUSTIN_PATH = '/resource/3syk-w9eu.json'
GIS_HOST = 'gis.traviscountytx.gov'
GIS_PATH = '/server1/rest/services/Boundaries_and_Jurisdictions/TCAD_public/MapServer/0/query'
AUSTIN_SELECT = 'permit_number,tcad_id,issue_date,permit_class_mapped,jurisdiction'
GIS_FIELDS = frozenset({'geo_id', 'PROP_ID', 'situs_address', 'situs_zip'})

class SourceBindingError(ValueError):
    pass


def _query(url, host, path, required):
    if not isinstance(url, str) or len(url) > 1500:
        raise SourceBindingError('missing/bounded source URL required')
    try:
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.hostname != host or parts.path != path
                or parts.username is not None or parts.password is not None
                or parts.fragment or parts.port is not None):
            raise SourceBindingError('unexpected source scheme/host/path/userinfo/port/fragment')
        entries = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except (ValueError, AttributeError) as exc:
        raise SourceBindingError('invalid source URL/query encoding') from exc
    if not entries or len(entries) != len(required) or set(k for k, _ in entries) != set(required):
        raise SourceBindingError('missing, duplicated, or extra source query parameter')
    return dict(entries)


def verified_query_urls(metadata, geo_ids, permit_count):
    """Return geo->feature query URL only after all declared URLs match their rows.

    This v1 evidence contract deliberately supports 1-2 geographic IDs; larger
    pagination and complete extracts require a new audited contract.
    """
    if type(permit_count) is not int or not 1 <= permit_count <= 3:
        raise SourceBindingError('v1 source proof bounded to three actual permit rows')
    if (not isinstance(geo_ids, tuple) or not 1 <= len(geo_ids) <= 2
            or tuple(sorted(set(geo_ids))) != geo_ids
            or not all(isinstance(g, str) and len(g) == 10 and g.isascii() and g.isdecimal() for g in geo_ids)):
        raise SourceBindingError('unambiguous sorted geographic IDs required')
    austin = _query(metadata.get('austin_url'), AUSTIN_HOST, AUSTIN_PATH,
                    {'$select', '$where', '$limit'})
    if austin != {'$select': AUSTIN_SELECT, '$where': 'tcad_id IS NOT NULL',
                  '$limit': str(permit_count)}:
        raise SourceBindingError('Austin selected fields/filter/page bound mismatch')
    if metadata.get('austin_completeness_contract') != 'EXPLICIT_LIMIT_3_NOT_EXHAUSTIVE_SOURCE':
        raise SourceBindingError('Austin full-source completeness must not be asserted')
    if metadata.get('gis_completeness_contract') != 'TWO_EXACT_GEO_ID_COUNT_QUERIES_EACH_COUNT_ONE' or len(geo_ids) != 2:
        raise SourceBindingError('GIS verification contract for the two IDs required')
    if set(metadata.get('gis_count_urls', {})) != set(geo_ids):
        raise SourceBindingError('exactly one count URL required for each geographic ID')
    if any(metadata['gis_counts'].get(g) != 1 for g in geo_ids):
        raise SourceBindingError('v1 verified GIS case expects one feature per ID')
    if not isinstance(metadata.get('gis_url_second'), str):
        raise SourceBindingError('second GIS feature source URL missing')
    result = {}
    for idx, geo in enumerate(geo_ids):
        feature_url = metadata['gis_url' if idx == 0 else 'gis_url_second']
        qs = _query(feature_url, GIS_HOST, GIS_PATH,
                    {'where', 'outFields', 'returnGeometry', 'f'})
        if (qs['where'] != "geo_id='%s'" % geo or
                set(qs['outFields'].split(',')) != GIS_FIELDS or
                len(qs['outFields'].split(',')) != len(GIS_FIELDS) or
                qs['returnGeometry'] != 'false' or qs['f'] != 'json'):
            raise SourceBindingError('GIS feature URL does not describe referenced geographic ID')
        count = _query(metadata['gis_count_urls'][geo], GIS_HOST, GIS_PATH,
                       {'where', 'returnCountOnly', 'f'})
        if count != {'where': "geo_id='%s'" % geo, 'returnCountOnly': 'true', 'f': 'json'}:
            raise SourceBindingError('GIS count URL is not an independent exact-ID count request')
        result[geo] = feature_url
    return result
