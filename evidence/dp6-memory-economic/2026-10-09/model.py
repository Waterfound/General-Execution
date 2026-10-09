#!/usr/bin/env python3
import json, math, sys

baseline={"work_s":3.079401,"watts":73.2,"usd":1000.0}
matrix=268435456
reads=1048576
contexts=math.floor(36_000_000_000/matrix)
bandwidth=1.2e12
traffic_low=528*1024**2
traffic_high=784*1024**2
work_per_w=baseline["work_s"]/baseline["watts"]
work_per_usd=baseline["work_s"]/baseline["usd"]

rows=[]
for latency_ns in [25,50,65,100,150,200,288.1,400]:
    q_rw=contexts/(reads*latency_ns*1e-9)
    q_full=min(contexts/(0.115+reads*latency_ns*1e-9),bandwidth/traffic_low)
    rows.append({
        "effective_latency_ns":latency_ns,
        "rw5_capacity_latency_upper_work_s":q_rw,
        "with_115ms_mh3_sensitivity_upper_work_s":q_full,
        "5x_max_whole_system_watts_at_this_q":q_full/(5*work_per_w),
        "5x_max_complete_system_usd_at_this_q":q_full/(5*work_per_usd),
    })

out={
  "contexts_36gb":contexts,
  "bandwidth_only_upper_work_s":{"784MiB":bandwidth/traffic_high,"528MiB":bandwidth/traffic_low},
  "latency_sensitivity":rows,
  "empirical_claim":False,
  "terminal":"COMPONENT_CALIBRATION_CANNOT_PROVE_COMPLETE_SPECIALIST_LCVW"
}
json.dump(out,sys.stdout,indent=2,sort_keys=True)
print()
