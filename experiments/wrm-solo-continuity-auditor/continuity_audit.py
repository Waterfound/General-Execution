#!/usr/bin/env python3
"""Read-only continuity surface audit for a software repository.

The auditor intentionally records secret *names* but never secret values. It uses
only Python's standard library and writes its report to stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SECRET_REF = re.compile(r"(?:secrets\.)([A-Z][A-Z0-9_]*)")
ENV_KEY_REF = re.compile(r"(?m)^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=")
CRON_REF = re.compile(r"cron\s*:\s*['\"]?([^'\"\n]+)")
USES_REF = re.compile(r"uses\s*:\s*([^\s#]+)")
URL_REF = re.compile(r"https?://([A-Za-z0-9.-]+)")

TEXT_SUFFIXES = {".yml", ".yaml", ".json", ".toml", ".md", ".txt", ".env", ".example"}
SKIP_PARTS = {".git", "node_modules", ".venv", "venv", "dist", "build"}


def readable_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.name.startswith(".env") or path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def provider_signals(relative: str, text: str) -> set[str]:
    # Comment-only examples describe possible configuration, not an observed
    # dependency. Keep prose/README evidence, but ignore shell/YAML/TOML
    # comment lines when scanning machine configuration.
    if Path(relative).suffix.lower() in {".yml", ".yaml", ".toml", ".env", ".example"}:
        text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    haystack = f"{relative}\n{text}".lower()
    mapping = {
        "aws": ("amazonaws.com", "aws-actions/", "aws_access_key"),
        "cloudflare": ("cloudflare", "wrangler"),
        "docker": ("docker/login-action", "docker build", "docker push"),
        "github": ("github.com", "github-actions", "ghcr.io"),
        "npm": ("npm publish", "registry.npmjs.org", "node_auth_token"),
        "paddle": ("paddle_api_key", "paddle.com", "@paddle/"),
        "pypi": ("pypa/gh-action-pypi-publish", "pypi.org"),
        "supabase": ("supabase_url", "supabase.com", "@supabase/"),
        "vercel": ("vercel", "vercel_token"),
    }
    return {name for name, needles in mapping.items() if any(n in haystack for n in needles)}


def audit(root: Path) -> dict:
    secrets: set[str] = set()
    configuration_identifiers: set[str] = set()
    schedules: set[str] = set()
    actions: set[str] = set()
    domains: set[str] = set()
    providers: set[str] = set()
    evidence_files: list[str] = []

    for path in readable_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found = False
        for match in SECRET_REF.findall(text):
            secrets.add(match)
            found = True
        for match in ENV_KEY_REF.findall(text):
            configuration_identifiers.add(match)
            found = True
        for match in CRON_REF.findall(text):
            schedules.add(match.strip())
            found = True
        for match in USES_REF.findall(text):
            actions.add(match.strip())
            found = True
        for match in URL_REF.findall(text):
            if not match.endswith(("github.com", "example.invalid")):
                domains.add(match.lower())
                found = True
        detected = provider_signals(relative, text)
        if detected:
            providers.update(detected)
            found = True
        if found:
            evidence_files.append(relative)

    declared = root / ".continuity.json"
    declaration = {}
    declaration_error = None
    if declared.exists():
        try:
            declaration = json.loads(declared.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            declaration_error = str(exc)

    required = {
        "successor_or_recovery_owner": declaration.get("successor_or_recovery_owner"),
        "private_repository_recovery": declaration.get("private_repository_recovery"),
        "restore_test_evidence": declaration.get("restore_test_evidence"),
        "domain_recovery_route": declaration.get("domain_recovery_route"),
        "payment_processor_recovery": declaration.get("payment_processor_recovery"),
    }
    gaps = [key for key, value in required.items() if not value]
    if declaration_error:
        gaps.append("valid_continuity_declaration")

    private_report = {
        "schema": "wrm.solo-continuity-audit.v0",
        "root": root.name,
        "observed": {
            "secret_identifiers_only": sorted(secrets),
            "configuration_identifiers_only": sorted(configuration_identifiers),
            "schedules": sorted(schedules),
            "external_actions": sorted(actions),
            "domains": sorted(domains),
            "providers": sorted(providers),
            "evidence_files": sorted(evidence_files),
        },
        "declared_controls": required,
        "gaps": sorted(set(gaps)),
        "limitations": [
            "No provider account, secret value, billing state, or restore success was inspected.",
            "Signals show operational dependencies, not ownership or recoverability.",
            "A clean report is not proof that a successor can operate the business.",
        ],
    }
    canonical = json.dumps(private_report, sort_keys=True, separators=(",", ":")).encode()
    private_report["public_attestation"] = {
        "algorithm": "sha256",
        "digest": hashlib.sha256(canonical).hexdigest(),
        "safe_to_publish": True,
        "statement": "Digest attests to this metadata-only report; it reveals no secret values.",
    }
    return private_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    print(json.dumps(audit(root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
