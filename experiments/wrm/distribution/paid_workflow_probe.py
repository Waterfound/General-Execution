"""Read-only quantitative proof for a public paid-workflow problem.

The counts are buyer-reported LOWER BOUNDS, not customer traces. No API,
payments, external I/O, account access or claim of diagnosed root cause.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json

POSTING = ("https://www.upwork.com/freelance-jobs/apply/"
           "Automation-Engineer-Needed-Audit-Google-Sheets-Apps-Script-"
           "Python-Windows-Machine-Controller_~022105471245779183596/")
QUOTAS = {"read_project_per_minute": 300, "read_user_per_minute": 60,
          "write_project_per_minute": 300, "write_user_per_minute": 60}
DAYS = 30

@dataclass(frozen=True)
class PublishedBuyerInput:
    min_api_calls: int = 390000
    min_value_reads: int = 347000
    min_value_updates: int = 40000
    days: int = DAYS
    low_job_preparation_minutes: int = 4
    high_job_preparation_minutes: int = 5
    offered_fixed_budget_usd: int = 500

    def __post_init__(self):
        for key in ("min_api_calls", "min_value_reads", "min_value_updates",
                    "days", "low_job_preparation_minutes",
                    "high_job_preparation_minutes", "offered_fixed_budget_usd"):
            val = getattr(self, key)
            if type(val) is not int or val <= 0:
                raise ValueError(f"{key}: require positive integer")
        if self.low_job_preparation_minutes > self.high_job_preparation_minutes:
            raise ValueError("job preparation range reversed")

def least_peak_possible(total: int, minutes: int) -> int:
    if type(total) is not int or total < 0 or type(minutes) is not int or minutes <= 0:
        raise ValueError("invalid integer counts")
    return (total + minutes - 1) // minutes

def hypothetical_batching(reads: int, savings_percent: int) -> dict:
    if type(reads) is not int or reads < 0 or type(savings_percent) is not int or not 0 <= savings_percent <= 100:
        raise ValueError("invalid hypothetical savings")
    saved = reads * savings_percent // 100
    return {"classification": "HYPOTHETICAL", "saved_calls": saved,
            "remaining_calls": reads - saved, "observed": False}

def hypothetical_one_job_economics(*, price="500", fee_percent="15", connects=8,
                                   connect_unit="0.15", nonlabor_cost="40", labor_per_hour="15") -> dict:
    try:
        p, fee, c, other, labor = [Decimal(v) for v in
                                    (price, fee_percent, connect_unit, nonlabor_cost, labor_per_hour)]
    except (ValueError, TypeError, InvalidOperation) as error:
        raise ValueError("invalid monetary input") from error
    if (any(not v.is_finite() for v in (p, fee, c, other, labor))
            or p <= 0 or not 0 <= fee <= 100 or c < 0 or other < 0 or labor <= 0
            or type(connects) is not int or connects < 0):
        raise ValueError("out-of-range monetary input")
    remaining = p * (1 - fee / 100) - c * connects - other
    return {"classification": "HYPOTHETICAL", "after_modelled_nonlabor_usd": str(remaining.quantize(Decimal(".01"))),
            "max_hours_before_modelled_labor_cost": str((remaining / labor).quantize(Decimal(".01"))),
            "taxes_fx_refunds_legal_expenses_included": False, "actual_contract": False}

def proof(buyer: PublishedBuyerInput = PublishedBuyerInput()) -> dict:
    minutes = buyer.days * 1440
    return {
        "schema": "rma.dist.public-buyer-quantitative-proof.v1",
        "source": POSTING, "evidence": "PUBLIC_BUYER_REPORTED_LOWER_BOUNDS",
        "offered_fixed_budget_usd": buyer.offered_fixed_budget_usd,
        "period_minutes": minutes,
        "calls_lower_bounds": {"total": buyer.min_api_calls, "reads": buyer.min_value_reads,
                               "updates": buyer.min_value_updates},
        "per_minute_averages_lower_bounds": {
            "all": round(buyer.min_api_calls / minutes, 3),
            "reads": round(buyer.min_value_reads / minutes, 3),
            "updates": round(buyer.min_value_updates / minutes, 3)},
        "least_possible_per_minute_peaks_for_exact_lower_bound_totals": {
            "total": least_peak_possible(buyer.min_api_calls, minutes),
            "reads": least_peak_possible(buyer.min_value_reads, minutes),
            "updates": least_peak_possible(buyer.min_value_updates, minutes)},
        "published_per_minute_quotas": QUOTAS,
        "quota_source": "https://developers.google.com/workspace/sheets/api/limits",
        "batching_source": "https://developers.google.com/workspace/sheets/api/guides/batch",
        "buyer_reported_job_preparation_minutes":
            [buyer.low_job_preparation_minutes, buyer.high_job_preparation_minutes],
        "root_cause_verified": False, "quota_exceeded_verified": False,
        "reason": "Monthly aggregate cannot identify minute bursts, request identity, read/write attribution, or job latency cause.",
        "counterexample": {
            "evenly_distributed_reads_can_fit_user_quota":
                least_peak_possible(buyer.min_value_reads, minutes) <= QUOTAS["read_user_per_minute"],
            "same_read_count_in_one_minute_exceeds_project_quota":
                buyer.min_value_reads > QUOTAS["read_project_per_minute"]},
        "next_evidence": ["per-minute API/429 traces", "per-user request identity", "job-id correlated timers",
                          "Sheets/Apps Script and Windows controller code", "serial timings", "retry/idempotence events"],
        "this_is_full_customer_audit": False, "buyer_wtp_for_waterfound_verified": False,
        "customers_acquired": 0, "actual_revenue_usd": "0", "outreach_authorized": False,
        "publication_authorized": False, "unattended_runtime_verified": False,
    }

if __name__ == "__main__":
    print(json.dumps({"buyer_proof": proof(),
                      "economic_scenarios": [hypothetical_one_job_economics(fee_percent=str(f)) for f in (0, 10, 15)],
                      "batching_example": hypothetical_batching(347000, 50)}, sort_keys=True, indent=2))
