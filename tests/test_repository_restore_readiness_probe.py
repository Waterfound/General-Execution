from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROBE = (
    Path(__file__).parents[1]
    / "experiments"
    / "repository-restore-readiness"
    / "probe.py"
)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


def fixture_bundle(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.email", "fixture@example.invalid")
    git(source, "config", "user.name", "Restore Fixture")
    (source / "README.md").write_text("restore fixture\n", encoding="utf-8")
    git(source, "add", "README.md")
    git(source, "commit", "-m", "fixture")
    git(source, "branch", "recovery-candidate")
    git(source, "tag", "v1")

    bundle = tmp_path / "fixture.bundle"
    git(source, "bundle", "create", str(bundle), "--all")
    expected = {
        "refs/heads/main": git(source, "rev-parse", "refs/heads/main"),
        "refs/heads/recovery-candidate": git(
            source, "rev-parse", "refs/heads/recovery-candidate"
        ),
        "refs/tags/v1": git(source, "rev-parse", "refs/tags/v1"),
    }
    return bundle, expected


def run_probe(bundle: Path, expected: dict[str, str]) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(PROBE), str(bundle)]
    for ref, object_id in expected.items():
        command.extend(["--expect-ref", f"{ref}={object_id}"])
    return subprocess.run(command, text=True, capture_output=True, check=False)


class RepositoryRestoreReadinessProbeTest(unittest.TestCase):
    def test_clean_room_restore_proves_refs_and_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle, expected = fixture_bundle(Path(directory))

            result = run_probe(bundle, expected)
            report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["result"], "pass")
            self.assertEqual(report["observed_refs"], expected)
            self.assertTrue(all(check["passed"] for check in report["checks"]))

    def test_missing_expected_ref_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle, expected = fixture_bundle(Path(directory))
            expected["refs/heads/absent"] = "0" * 40

            result = run_probe(bundle, expected)
            report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(report["result"], "fail")
            expected_check = next(
                check for check in report["checks"] if check["name"] == "expected_refs"
            )
            self.assertEqual(expected_check["missing"], ["refs/heads/absent"])


if __name__ == "__main__":
    unittest.main()
