import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from maintenance import seccomp_profile as tool


class ScopedProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / 'host'
        self.receipts = self.root / 'receipts'
        self.target.mkdir(mode=0o755)
        self.receipts.mkdir()
        self.now = datetime(2026, 11, 6, 15, tzinfo=timezone.utc)
        self.data = (Path(__file__).parents[1] / 'maintenance/profiles/patchright-6a1e2c43.json').read_bytes()
        self.request = dict(schema_version=1, node='pc2', node_uid='11111111-1111-1111-1111-111111111111',
                            run_id='patchright-test', profile_sha256=tool.PROFILE_SHA256,
                            expires_at=(self.now + timedelta(minutes=30)).isoformat())

    def run_tool(self, request=None, data=None, actual_node='pc2'):
        return tool.provision(request or self.request, self.data if data is None else data,
                              self.target, self.receipts, actual_node, self.request['node_uid'], lambda: self.now)

    def test_exact_profile_installed_read_back_and_durable_receipt(self):
        self.assertEqual(len(self.data), 9218)
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), tool.PROFILE_SHA256)
        receipt = self.run_tool()
        self.assertEqual(receipt['action'], 'installed_new_profile')
        self.assertFalse(receipt['native_qualified'])
        target = self.target / tool.FILENAME
        self.assertEqual(target.read_bytes(), self.data)
        self.assertEqual(target.stat().st_mode & 0o222, 0)
        stored = json.loads((self.receipts / self.request['run_id'] / 'receipt.json').read_text())
        self.assertEqual(stored, receipt)
        self.assertEqual(sorted(p.name for p in self.target.iterdir()), [tool.FILENAME])

    def test_existing_exact_profile_adopted_without_overwrite_and_run_never_replayed(self):
        first = self.run_tool()
        before = (self.target / tool.FILENAME).stat()
        with self.assertRaises(FileExistsError):
            self.run_tool()
        successor = dict(self.request, run_id='patchright-successor')
        self.assertEqual(self.run_tool(successor)['action'], 'existing_exact_read_only_profile')
        self.assertEqual((self.target / tool.FILENAME).stat().st_ino, before.st_ino)

    def test_modified_input_and_request_reject_before_output(self):
        variants = [dict(self.request, node='obs2'), dict(self.request, node_uid='wrong'),
                    dict(self.request, schema_version=True), dict(self.request, run_id='../escape'),
                    dict(self.request, profile_sha256='a' * 64), dict(self.request, extra=True),
                    dict(self.request, expires_at=self.now.isoformat()),
                    dict(self.request, expires_at=(self.now + timedelta(hours=2)).isoformat()),
                    dict(self.request, expires_at='2026-11-06T15:30:00')]
        for request in variants:
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.run_tool(request)
        with self.assertRaises(ValueError):
            self.run_tool(actual_node='obs2')
        with self.assertRaises(ValueError):
            self.run_tool(data=self.data[:-1] + b'x')
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertEqual(list(self.receipts.iterdir()), [])

    def test_existing_symlink_wrong_bytes_writable_or_hardlink_are_never_replaced(self):
        for kind in ['symlink', 'bytes', 'writable', 'hardlink']:
            with self.subTest(kind=kind):
                target = self.target / tool.FILENAME
                other = self.root / ('other-' + kind)
                other.write_bytes(self.data)
                if kind == 'symlink':
                    target.symlink_to(other)
                elif kind == 'hardlink':
                    other.chmod(0o444)
                    os.link(other, target)
                else:
                    target.write_bytes(b'wrong' if kind == 'bytes' else self.data)
                    target.chmod(0o444 if kind == 'bytes' else 0o644)
                before = target.lstat()
                with self.assertRaises((OSError, ValueError)):
                    self.run_tool(dict(self.request, run_id='patchright-' + kind))
                self.assertEqual(target.lstat().st_ino, before.st_ino)
                target.unlink()

    def test_unsafe_target_directory_refused_before_intent(self):
        self.target.chmod(0o777)
        with self.assertRaises(ValueError):
            self.run_tool()
        self.assertEqual(list(self.receipts.iterdir()), [])

    def test_expiry_between_intent_and_publish_prevents_activation(self):
        times = iter([self.now, self.now + timedelta(hours=2)])
        with self.assertRaises(ValueError):
            tool.provision(self.request, self.data, self.target, self.receipts, 'pc2', self.request['node_uid'], lambda: next(times))
        self.assertFalse((self.target / tool.FILENAME).exists())
        run = self.receipts / self.request['run_id']
        self.assertTrue((run / 'intent.json').exists())
        self.assertFalse((run / 'receipt.json').exists())

    def test_publication_race_never_replaces_concurrent_destination(self):
        original = os.link
        def race(src, dst, **kwargs):
            (self.target / dst).write_bytes(b'concurrent')
            return original(src, dst, **kwargs)
        with patch.object(tool.os, 'link', side_effect=race), self.assertRaises(FileExistsError):
            self.run_tool()
        self.assertEqual((self.target / tool.FILENAME).read_bytes(), b'concurrent')
        self.assertFalse((self.receipts / self.request['run_id'] / 'receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
