"""CR-001 bounded GIS QC baseline probe (not a product or ISO 19157 certification).

Uses Shapely as a direct free substitute. All geometries in the executable
probe are synthetic and labeled; buyer data and external truth are unavailable.
"""
from __future__ import annotations
import hashlib
import json
from shapely.geometry import Polygon
from shapely.validation import explain_validity
from shapely import make_valid

SCHEMA = 'cr001.gis-substitution-probe.v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inspect(features):
    if not isinstance(features, list) or not 0 < len(features) <= 1000:
        raise ValueError('bounded feature list required')
    seen = set()
    issues = []
    for item in features:
        if not isinstance(item, dict) or set(item) != {'id', 'geometry'}:
            raise ValueError('strict feature schema required')
        fid, g = item['id'], item['geometry']
        if not isinstance(fid, str) or not fid or fid in seen:
            raise ValueError('duplicate or invalid feature id')
        seen.add(fid)
        if g is not None and not isinstance(g, Polygon):
            raise ValueError('Polygon or null required')
        if g is None or g.is_empty:
            issues.append({'id': fid, 'kind': 'NULL_OR_EMPTY', 'action': 'NEVER_FIX', 'reason': 'source geometry absent'})
        elif not g.is_valid:
            # make_valid can change type/area/feature count; no silent write
            candidate = make_valid(g)
            issues.append({'id': fid, 'kind': 'INVALID_GEOMETRY', 'action': 'REVIEW_ONLY',
                           'reason': explain_validity(g), 'proposed_type': candidate.geom_type,
                           'change_requires_approval': True})
    for i, a in enumerate(features):
        for b in features[i+1:]:
            ga, gb = a['geometry'], b['geometry']
            if ga is not None and gb is not None and ga.is_valid and gb.is_valid and ga.area > 0 and gb.area > 0 and ga.intersection(gb).area > 0:
                issues.append({'id': a['id'] + '|' + b['id'], 'kind': 'OVERLAP',
                               'action': 'NEVER_FIX', 'reason': 'without layer semantics overlap may be intentional'})
    return {'schema': SCHEMA, 'features': len(features), 'issues': issues,
            'originals_untouched': True, 'repairs_applied': 0,
            'ground_truth_type': 'SYNTHETIC_ONLY', 'buyer_acceptance_proven': False,
            'competitive_superiority_proven': False}


def buyer_requirements():
    # Values are transcribed from the public buyer's spec, not measured outcomes.
    features, seconds, defects = 5_000_000, 30 * 60, 2_000
    return {'budget_usd_posted': 1000, 'feature_target': features,
            'throughput_required_features_per_second': features/seconds,
            'reference_defects': defects, 'min_detected_for_recall_95pct': 1900,
            'max_clean_control_false_positive_rate': 0.02,
            'no_unrequested_changes': True, 'fully_reversible_repairs': True,
            'reference_benchmark_available': False,
            'competition': 'SHAPELY_DIRECT_BASELINE; QGIS_NOT_EXECUTED',
            'commercial_decision': 'HOLD_SCOPE_AND_UNVERIFIED_DIFFERENTIATION'}


def demo():
    p = lambda coords: Polygon(coords)
    data = [
        {'id': 'clean', 'geometry': p([(0, 0), (1, 0), (1, 1), (0, 1)])},
        {'id': 'overlap', 'geometry': p([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)])},
        {'id': 'bowtie', 'geometry': p([(3, 0), (4, 1), (3, 1), (4, 0)])},
        {'id': 'missing', 'geometry': None},
    ]
    result = inspect(data)
    result['buyer_spec'] = buyer_requirements()
    result['synthetic_issues_observed'] = sorted((x['kind'], x['id']) for x in result['issues'])
    result['synthetic_issues_digest'] = digest(result['synthetic_issues_observed'])
    return result

if __name__ == '__main__':
    print(json.dumps(demo(), indent=2, sort_keys=True))
