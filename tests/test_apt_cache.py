import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'maintenance'))
from apt_cache import inventory, run, MIN_AGE


class Receipt:
    def __init__(self):
        self.saved, self.events = {}, []
    def save(self, name, data):
        self.saved[name] = data
    def emit(self, event, **data):
        self.events.append((event, data))


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        (self.path / 'lock').touch()
        self.now = int(time.time())
        self.env = patch.dict(os.environ, {'NODE_NAME': 'test-node'})
        self.env.start()
        self.addCleanup(self.env.stop)
    def old(self, name='package_1_amd64.deb'):
        p = self.path / name
        p.write_bytes(b'download')
        os.utime(p, (self.now-MIN_AGE-30,)*2)
        return p
    def plan(self):
        r = Receipt()
        run(r, 'cache-plan', path=str(self.path), now=self.now)
        return r.saved['cache-plan.json']
    def apply(self, plan, **changes):
        policy = {'node': 'test-node', 'approval_reference': 'operator-review',
                  'reference_inventory_complete': True, 'created_at': self.now-10,
                  'expires_at': self.now+60, 'plan': plan, **changes}
        r = Receipt()
        run(r, 'cache-apply', policy, plan['plan_sha256'], str(self.path), self.now)
        return r
    def test_only_old_regular_single_link_debs(self):
        p = self.old()
        (self.path/'fresh.deb').touch()
        self.old('receipt.json')
        (self.path/'symlink.deb').symlink_to(p)
        linked = self.old('linked.deb')
        os.link(linked, self.path/'other-name')
        (self.path/'partial').mkdir()
        self.assertEqual([p.name], [f['name'] for f in self.plan()['files']])
        self.assertTrue(p.exists())
    def test_apply_removes_exact_cache_preserves_everything_else(self):
        p=self.old(); self.old('receipt.json')
        r=self.apply(self.plan())
        self.assertFalse(p.exists())
        self.assertTrue((self.path/'receipt.json').exists())
        self.assertTrue((self.path/'lock').exists())
        self.assertEqual('cache_completed', r.events[-1][0])
        self.assertIn('guard-proposal.json', r.saved)
    def test_changed_new_or_replaced_files_abort_without_removing(self):
        for change in ('modify', 'add', 'replace'):
            with self.subTest(change=change):
                p=self.old(); plan=self.plan()
                if change=='modify': p.write_bytes(b'changed')
                if change=='add': self.old('added.deb')
                if change=='replace':
                    replacement=self.old('replacement.deb')
                    os.replace(replacement, p)
                with self.assertRaises(ValueError): self.apply(plan)
                self.assertTrue(p.exists())
                (self.path/'added.deb').unlink(missing_ok=True)
    def test_missing_authority_wrong_node_expiry_and_reference_guard(self):
        p=self.old(); plan=self.plan()
        for changes in ({'approval_reference':''}, {'node':'other'},
                        {'expires_at':self.now}, {'reference_inventory_complete':False}):
            with self.assertRaises(ValueError): self.apply(plan, **changes)
            self.assertTrue(p.exists())
    def test_symlink_lock_and_directory_rejected(self):
        (self.path/'lock').unlink()
        (self.path/'lock').symlink_to(self.path/'missing')
        with self.assertRaises(OSError): self.plan()
        link=self.path/'alias'; link.symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(OSError): run(Receipt(), 'cache-plan', path=str(link), now=self.now)
    def test_posix_lock_contention_aborts(self):
        import subprocess
        proc=subprocess.Popen([sys.executable,'-c',
          'import fcntl,sys; f=open(sys.argv[1],"r+"); fcntl.lockf(f,fcntl.LOCK_EX); print("held",flush=True); sys.stdin.read()',
          str(self.path/'lock')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual('held',proc.stdout.readline().strip())
            with self.assertRaises(BlockingIOError): self.plan()
        finally:
            proc.communicate('release',timeout=5)


if __name__ == '__main__':
    unittest.main()
