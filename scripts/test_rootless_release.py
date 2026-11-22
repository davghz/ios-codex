import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rootless_version import package_name, package_revision


spec = importlib.util.spec_from_file_location("sync", Path(__file__).with_name("sync-rootless-releases.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def release(version, revision):
    filename = package_name(version, revision)
    return {
        "tag_name": f"v{version}-{revision}-rootless", "draft": False, "prerelease": False,
        "assets": [{"name": name, "state": "uploaded"} for name in (filename, filename + ".sha256")],
    }


class RootlessReleaseTests(unittest.TestCase):
    def test_discover_missing_revision_without_rebuilding_older_packages(self):
        published = [release("0.170.0", 2), release("0.171.0", 1)]
        tags = [{"tagName": "rust-v" + v} for v in ("0.170.0", "0.171.0", "0.172.0")]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            with patch.object(sync, "releases", return_value=published), patch.object(sync, "gh_json", return_value=tags), patch.dict(os.environ, GITHUB_OUTPUT=str(output)):
                sync.discover("test/repo", "")
            self.assertIn('"version":"0.171.0"', output.read_text())
            self.assertIn('"version":"0.172.0"', output.read_text())
            self.assertNotIn('"version":"0.170.0"', output.read_text())

    def test_publish_latest_revision_once_and_ignore_stale_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp)
            for rev in (1, 2):
                (artifacts / package_name("0.171.0", rev)).touch()
            existing = [release("0.171.0", 1)]
            with patch.object(sync, "releases", return_value=existing), patch.object(sync, "publish_release") as publish_release:
                self.assertEqual(sync.publish("test/repo", artifacts), 0)
                self.assertEqual(publish_release.call_count, 1)
                self.assertTrue(publish_release.call_args.args[-1])
                existing.append(release("0.171.0", 2))
                self.assertEqual(sync.publish("test/repo", artifacts), 0)
                self.assertEqual(publish_release.call_count, 1)
            self.assertEqual(package_revision("0.172.0"), 1)
