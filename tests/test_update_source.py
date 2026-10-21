import copy
import hashlib
import importlib.util
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile


spec = importlib.util.spec_from_file_location("update_source", Path(__file__).parents[1] / "scripts/update_source.py")
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.release = {
            "draft": False, "prerelease": False, "tag_name": "v9.8.7",
            "name": "BCD 9.8.7", "published_at": "2026-10-21T05:11:39Z", "body": "Release notes",
            "assets": [{
                "name": "BCD.ipa", "id": 42, "size": 3,
                "digest": "sha256:" + hashlib.sha256(b"ipa").hexdigest(),
                "browser_download_url": "https://github.com/thebcd69/bcd-games/releases/download/v9.8.7/BCD.ipa",
                "updated_at": "2026-10-21T05:11:39Z",
            }],
        }

    def test_reject_incomplete_or_unstable_release(self):
        for change in ({"draft": True}, {"prerelease": True}, {"assets": []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                source.release_state(self.release | change)
        for change in ({"digest": None}, {"browser_download_url": "https://example.com/BCD.ipa"}):
            release = copy.deepcopy(self.release)
            release["assets"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                source.release_state(release)

    def test_detect_notes_and_replaced_assets_but_ignore_download_count(self):
        state = source.release_state(self.release)
        release = copy.deepcopy(self.release)
        release["assets"][0]["download_count"] = 100
        self.assertEqual(source.release_state(release), state)
        release["body"] = "Updated notes"
        self.assertNotEqual(source.release_state(release), state)
        release = copy.deepcopy(self.release)
        release["assets"][0]["id"] = 43
        self.assertNotEqual(source.release_state(release), state)

    def test_reject_corrupted_download(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "BCD.ipa"
            path.write_bytes(b"ipa")
            source.verify_ipa(path, self.release["assets"][0])
            path.write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError, "checksum"):
                source.verify_ipa(path, self.release["assets"][0])
            path.write_bytes(b"truncated")
            with self.assertRaisesRegex(ValueError, "size"):
                source.verify_ipa(path, self.release["assets"][0])

    def test_read_actual_versions_and_extension_permissions(self):
        main = {
            "CFBundleExecutable": "BCD", "CFBundleIdentifier": "example.BCD",
            "CFBundleShortVersionString": "1.2.3", "CFBundleVersion": "456",
            "MinimumOSVersion": "18.0", "NSMicrophoneUsageDescription": "Record audio",
        }
        extension = {"CFBundleExecutable": "Helper", "NSLocalNetworkUsageDescription": "Connect locally"}
        with tempfile.TemporaryDirectory() as temp:
            ipa = Path(temp) / "BCD.ipa"
            with zipfile.ZipFile(ipa, "w") as archive:
                archive.writestr("Payload/BCD.app/Info.plist", plistlib.dumps(main))
                archive.writestr("Payload/BCD.app/BCD", b"main executable")
                archive.writestr("Payload/BCD.app/PlugIns/Helper.appex/Info.plist", plistlib.dumps(extension))
                archive.writestr("Payload/BCD.app/PlugIns/Helper.appex/Helper", b"extension executable")
            signatures = [
                subprocess.CompletedProcess([], 0, stdout=plistlib.dumps({"get-task-allow": True})),
                subprocess.CompletedProcess([], 0, stdout=plistlib.dumps({"com.apple.security.application-groups": ["group.test"]})),
            ]
            with patch.object(source.subprocess, "run", side_effect=signatures):
                info, permissions = source.inspect_ipa(ipa)
            feed = source.make_source(source.release_state(self.release), info, permissions)
            app = feed["apps"][0]
            self.assertEqual(app["bundleIdentifier"], "example.BCD")
            self.assertEqual(app["versions"][0]["version"], "1.2.3")
            self.assertEqual(app["versions"][0]["buildVersion"], "456")
            self.assertEqual(app["versions"][0]["minOSVersion"], "18.0")
            self.assertEqual(permissions["entitlements"], ["com.apple.security.application-groups", "get-task-allow"])
            self.assertEqual(permissions["privacy"], {"NSMicrophoneUsageDescription": "Record audio", "NSLocalNetworkUsageDescription": "Connect locally"})
            with patch.object(source.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "codesign")):
                with self.assertRaises(subprocess.CalledProcessError):
                    source.inspect_ipa(ipa)


if __name__ == "__main__":
    unittest.main()
