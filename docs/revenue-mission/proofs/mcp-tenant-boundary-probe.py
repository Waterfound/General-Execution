#!/usr/bin/env python3
"""Synthetic proof for tenant-boundary and destructive-action MCP invariants.

This is deliberately model-independent. It compares a vulnerable adapter that
trusts client-supplied tenant identifiers with a hardened adapter that binds
tenant scope and destructive approval to authenticated server-side context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


DATA = {
    "acme": {"invoice-1": {"total": 125}},
    "bravo": {"invoice-9": {"total": 900}},
}


@dataclass(frozen=True)
class Context:
    principal: str
    tenant: str
    permissions: frozenset[str]
    approved_actions: frozenset[str] = frozenset()


SCENARIOS = [
    {
        "id": "authorized_read",
        "tool": "read_invoice",
        "context": Context("alice", "acme", frozenset({"invoice:read"})),
        "args": {"tenant": "acme", "invoice_id": "invoice-1"},
        "expect": "allow",
    },
    {
        "id": "cross_tenant_read",
        "tool": "read_invoice",
        "context": Context("alice", "acme", frozenset({"invoice:read"})),
        "args": {"tenant": "bravo", "invoice_id": "invoice-9"},
        "expect": "deny",
    },
    {
        "id": "unconfirmed_destructive_action",
        "tool": "delete_invoice",
        "context": Context("alice", "acme", frozenset({"invoice:delete"})),
        "args": {"tenant": "acme", "invoice_id": "invoice-1"},
        "expect": "deny",
    },
    {
        "id": "confirmed_destructive_action",
        "tool": "delete_invoice",
        "context": Context(
            "alice",
            "acme",
            frozenset({"invoice:delete"}),
            frozenset({"delete_invoice:invoice-1"}),
        ),
        "args": {"tenant": "acme", "invoice_id": "invoice-1"},
        "expect": "allow",
    },
]


def vulnerable_adapter(tool: str, context: Context, args: dict[str, str]) -> str:
    """Anti-pattern: tenant and destructive authority come from call arguments."""
    tenant = args["tenant"]
    if tool == "read_invoice":
        return "allow" if args["invoice_id"] in DATA.get(tenant, {}) else "deny"
    if tool == "delete_invoice":
        return "allow" if args["invoice_id"] in DATA.get(tenant, {}) else "deny"
    return "deny"


def hardened_adapter(tool: str, context: Context, args: dict[str, str]) -> str:
    """Reference invariant: server context owns tenant and action authority."""
    if args.get("tenant") != context.tenant:
        return "deny"
    invoice_id = args.get("invoice_id", "")
    if invoice_id not in DATA.get(context.tenant, {}):
        return "deny"
    if tool == "read_invoice":
        return "allow" if "invoice:read" in context.permissions else "deny"
    if tool == "delete_invoice":
        action = f"delete_invoice:{invoice_id}"
        authorized = "invoice:delete" in context.permissions
        confirmed = action in context.approved_actions
        return "allow" if authorized and confirmed else "deny"
    return "deny"


def evaluate(name: str, adapter: Callable[[str, Context, dict[str, str]], str]) -> dict[str, Any]:
    observations = []
    for scenario in SCENARIOS:
        actual = adapter(scenario["tool"], scenario["context"], scenario["args"])
        observations.append(
            {
                "scenario": scenario["id"],
                "expected": scenario["expect"],
                "actual": actual,
                "pass": actual == scenario["expect"],
            }
        )
    return {
        "adapter": name,
        "passed": sum(item["pass"] for item in observations),
        "total": len(observations),
        "observations": observations,
    }


def main() -> int:
    report = {
        "predicate": "detect cross-tenant reads and unconfirmed destructive actions",
        "vulnerable": evaluate("client-supplied-tenant", vulnerable_adapter),
        "hardened": evaluate("server-bound-tenant", hardened_adapter),
    }
    detected = [
        item["scenario"]
        for item in report["vulnerable"]["observations"]
        if not item["pass"]
    ]
    report["result"] = {
        "vulnerabilities_detected": detected,
        "hardened_all_pass": report["hardened"]["passed"] == report["hardened"]["total"],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    expected = {"cross_tenant_read", "unconfirmed_destructive_action"}
    return 0 if set(detected) == expected and report["result"]["hardened_all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
