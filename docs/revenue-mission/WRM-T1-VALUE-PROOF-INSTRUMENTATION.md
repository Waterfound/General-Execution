# WRM-T1 Value Proof instrumentation

Status: candidate-level measurement contract. Capability evidence is not ROI evidence.

## Required observation per representative workflow

Record only observed facts:
- workflow_id and representative_workflow_class
- intent_timestamp and terminal_timestamp
- terminal_state
- machine_state_transitions
- process_invocations
- human_interventions_requested
- human_interventions_genuinely_required
- observable_human_active_minutes
- retries
- rework_events
- recovery_events
- provenance_items_expected
- provenance_items_present
- autonomous_resolutions
- resolution_opportunities

Unknown or unobserved values MUST be null, never estimated.

## Natural comparable

A delta may be computed only when a naturally occurring comparable exists with materially matched scope and outcome. Record comparable_id and comparability_notes. Never manufacture an inefficient manual baseline.

## Derived metrics

When inputs are observed:
- mission_completion_latency = terminal_timestamp - intent_timestamp
- autonomous_resolution_rate = autonomous_resolutions / resolution_opportunities
- provenance_coverage = provenance_items_present / provenance_items_expected
- recovery_improvement, avoidable_rework_reduced, coordination_tax_removed, operator_hours_saved, latency_reduced, and control_plane_leverage remain null unless a valid natural comparable supports the calculation.

Use conservative lower bounds where uncertainty remains. Preserve raw observations alongside every derivation.

## Claim boundary

Existing unattended pilot, core rehearsal, GOP and Holistic Symbiosis evidence establish governed capability only. They do not establish approvals eliminated, operator-hours saved, matched latency reduction, counterfactual rework avoided, monetary risk reduction, ROI, or willingness to pay.

Pricing remains gated on measured economic value plus real willingness-to-pay evidence.
