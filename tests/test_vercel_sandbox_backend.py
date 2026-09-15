import sys
from types import ModuleType

import pytest

from general_execution.vercel_sandbox import (
    GENERAL_EXECUTION_REPOSITORY_URL,
    VERCEL_SANDBOX_RUNTIME,
    VERCEL_SANDBOX_TIMEOUT_MS,
    VercelSandboxConformanceError,
    VercelSandboxConformanceSpec,
    _default_sandbox_factory,
)

REVISION = "c" * 40


def install_fake_vercel(monkeypatch, sandbox_class):
    package = ModuleType("vercel")
    package.__path__ = []
    submodule = ModuleType("vercel.sandbox")
    submodule.Sandbox = sandbox_class
    monkeypatch.setitem(sys.modules, "vercel", package)
    monkeypatch.setitem(sys.modules, "vercel.sandbox", submodule)


def test_default_factory_binds_exact_git_source_runtime_timeout_and_credentials(monkeypatch):
    captured = []
    sentinel = object()

    class FakeSDK:
        @classmethod
        def create(cls, **kwargs):
            captured.append(kwargs)
            return sentinel

    install_fake_vercel(monkeypatch, FakeSDK)
    spec = VercelSandboxConformanceSpec(REVISION)
    actual = _default_sandbox_factory(
        spec,
        "token-secret",
        "team_MHwznJgPOms2fJdgTInc1WZG",
        "prj_general_execution",
    )

    assert actual is sentinel
    assert captured == [
        {
            "runtime": VERCEL_SANDBOX_RUNTIME,
            "source": {
                "type": "git",
                "url": GENERAL_EXECUTION_REPOSITORY_URL,
                "revision": REVISION,
            },
            "timeout": VERCEL_SANDBOX_TIMEOUT_MS,
            "token": "token-secret",
            "team_id": "team_MHwznJgPOms2fJdgTInc1WZG",
            "project_id": "prj_general_execution",
        }
    ]


def test_default_factory_omits_unsupplied_credentials(monkeypatch):
    captured = []
    sentinel = object()

    class FakeSDK:
        @classmethod
        def create(cls, **kwargs):
            captured.append(kwargs)
            return sentinel

    install_fake_vercel(monkeypatch, FakeSDK)
    spec = VercelSandboxConformanceSpec(REVISION)
    _default_sandbox_factory(spec, None, None, None)

    assert "token" not in captured[0]
    assert "team_id" not in captured[0]
    assert "project_id" not in captured[0]
    assert captured[0]["source"]["revision"] == REVISION


def test_default_factory_translates_sdk_creation_failure_without_fabricating_run(monkeypatch):
    class FailingSDK:
        @classmethod
        def create(cls, **kwargs):
            raise RuntimeError("provider unavailable")

    install_fake_vercel(monkeypatch, FailingSDK)
    spec = VercelSandboxConformanceSpec(REVISION)
    with pytest.raises(VercelSandboxConformanceError, match="creation failed"):
        _default_sandbox_factory(spec, None, None, None)
