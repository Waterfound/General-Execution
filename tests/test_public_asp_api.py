"""Keep the two candidate ASP APIs from silently overwriting one another."""

import general_execution as ge
from general_execution import asp_transition, asp_transition_engine
from importlib import import_module


def test_runtime_asp_exports_are_the_types_consumed_by_resume_tick():
    runtime = import_module("general_execution.resume_tick")
    assert ge.AspTransitionError is asp_transition.AspTransitionError
    assert ge.PassiveWakeAdmission is runtime.PassiveWakeAdmission
    assert ge.admit_passive_wake is asp_transition.admit_passive_wake
    assert ge.apply_active_transition is runtime.apply_active_transition
    assert ge.SignalAspTransitionError is asp_transition_engine.AspTransitionError
    assert ge.SignalPassiveWakeAdmission is asp_transition_engine.PassiveWakeAdmission
    assert ge.admit_passive_wake_signal is asp_transition_engine.admit_passive_wake
    assert ge.PassiveWakeAdmission is not ge.SignalPassiveWakeAdmission


def test_public_exports_are_unique_and_resolve():
    assert len(ge.__all__) == len(set(ge.__all__))
    assert all(hasattr(ge, name) for name in ge.__all__)
