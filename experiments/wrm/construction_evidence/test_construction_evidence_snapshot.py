import os
import tempfile
import unittest
from pathlib import Path

from construction_evidence_snapshot import diff, snapshot


class EvidenceSnapshotTest(unittest.TestCase):
    def test_exact_change_classes_without_editing_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "unchanged.pdf").write_bytes(b"same")
            (root / "rename me.pdf").write_bytes(b"rename-body")
            (root / "same-size.pdf").write_bytes(b"AAAA")
            (root / "remove.pdf").write_bytes(b"removed")
            before = snapshot(root, observed_at="2026-10-16T00:00:00Z")

            (root / "rename me.pdf").rename(root / "rename-me.pdf")
            (root / "same-size.pdf").write_bytes(b"BBBB")
            (root / "remove.pdf").unlink()
            (root / "added.pdf").write_bytes(b"added")
            after = snapshot(root, observed_at="2026-10-16T12:00:00Z")

            result = diff(before, after)
            self.assertEqual([x["path"] for x in result["added"]], ["added.pdf"])
            self.assertEqual([x["path"] for x in result["removed"]], ["remove.pdf"])
            self.assertEqual(result["renamed"][0]["from"], "rename me.pdf")
            self.assertEqual(result["renamed"][0]["to"], "rename-me.pdf")
            self.assertEqual(result["content_changed"][0]["path"], "same-size.pdf")
            self.assertTrue(result["content_changed"][0]["same_size"])

    def test_timestamp_only_change_is_not_content_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "plan.pdf"
            path.write_bytes(b"identical")
            before = snapshot(root, observed_at="2026-10-16T00:00:00Z")
            stat = path.stat()
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
            after = snapshot(root, observed_at="2026-10-16T12:00:00Z")
            result = diff(before, after)
            self.assertEqual(result["content_changed"], [])
            self.assertEqual(result["metadata_only"][0]["path"], "plan.pdf")

    def test_duplicate_hash_move_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pdf").write_bytes(b"duplicate")
            (root / "b.pdf").write_bytes(b"duplicate")
            before = snapshot(root, observed_at="2026-10-16T00:00:00Z")
            (root / "a.pdf").unlink()
            (root / "b.pdf").unlink()
            (root / "c.pdf").write_bytes(b"duplicate")
            (root / "d.pdf").write_bytes(b"duplicate")
            after = snapshot(root, observed_at="2026-10-16T12:00:00Z")
            result = diff(before, after)
            self.assertEqual(result["renamed"], [])
            self.assertEqual(len(result["added"]), 2)
            self.assertEqual(len(result["removed"]), 2)


if __name__ == "__main__":
    unittest.main()
