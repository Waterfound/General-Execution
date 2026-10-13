"""Deterministic synthetic same-input comparison: candidate O(n²) vs native Shapely STRtree.
No source/buyer dataset, no vendor superiority, no 5M scale claim.
"""
from __future__ import annotations
import json, statistics, time, platform, tracemalloc
from shapely.geometry import box
from shapely.strtree import STRtree
from shapely import __version__ as shapely_version
from gis_probe import inspect


def fixture(n):
    # Separately labeled synthetic cells: exactly 2 overlaps, no random truth artifacts.
    if n < 6: raise ValueError('n >=6')
    grid=[{'id':f'g{i:04}', 'geometry':box((i%64)*3,(i//64)*3,(i%64)*3+1,(i//64)*3+1)} for i in range(n)]
    grid[-1]['geometry']=box(.5,.5,1.5,1.5) # overlaps first, potentially also no others
    grid[-2]['geometry']=box(3.5,.5,4.5,1.5) # overlaps second
    return grid


def shapely_baseline(features):
    # Official free library spatial query, not a second Waterfound differentiator.
    polys=[f['geometry'] for f in features]
    tree=STRtree(polys)
    issues=[]
    for i,g in enumerate(polys):
        for j in tree.query(g):
            j=int(j)
            if j>i and g.intersection(polys[j]).area>0:
                issues.append((features[i]['id'],features[j]['id']))
    return sorted(issues)


def candidate_pairs(features):
    return sorted(tuple(x['id'].split('|')) for x in inspect(features)['issues'] if x['kind']=='OVERLAP')


def execute():
    measured=[]
    for n in (20,60,100,180):
        data=fixture(n)
        cand_times=[]; native_times=[]
        for _ in range(2):
            t=time.perf_counter(); got=candidate_pairs(data);cand_times.append(time.perf_counter()-t)
            t=time.perf_counter(); native=shapely_baseline(data);native_times.append(time.perf_counter()-t)
            if got != native:raise AssertionError(f'disagree at {n}: {got} vs {native}')
            if len(got)!=2:raise AssertionError(f'expected two synthetic overlaps {got}')
        measured.append({'features':n,'equal_pair_sets':True,'ground_truth':'synthetic_two_overlap_pairs',
                         'pairs_detected':len(got),'candidate_median_ms':round(1000*statistics.median(cand_times),3),
                         'free_strtree_median_ms':round(1000*statistics.median(native_times),3),
                         'ratio_candidate_over_free':round(statistics.median(cand_times)/statistics.median(native_times),2)})
    return {'schema':'cr001.synthetic.same-input.native-substitute.v1','python':platform.python_version(),
            'shapely':shapely_version,'benchmark_cases':measured,'source_data':'SYNTHETIC_ONLY',
            'repetitions':2,'machines':'current local container','buyer_data':False,
            '5m_30min_benchmark':False,'qgis_executed':False,'external_acceptance':False,
            'competitive_advantage':False,'decision':'KILL_GENERIC_GIS_OVERLAP_VALIDATOR_AS_FIRST_PRODUCT'}


if __name__=='__main__': print(json.dumps(execute(),indent=2,sort_keys=True))
