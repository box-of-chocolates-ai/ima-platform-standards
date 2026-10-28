import copy
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'maintenance'))
from journals import run, MIN_AGE
from test_apt_cache import Receipt


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.src = root/'source'; self.src.mkdir()
        self.arc = root/'archive'; self.arc.mkdir()
        self.now = int(time.time())
        self.env = patch.dict(os.environ, {'NODE_NAME':'obs2'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.policy = {'node':'obs2','approval_reference':'user-exact-archive-review',
                       'approved_by':'operator','reference_inventory_complete':True,
                       'created_at':self.now-5,'expires_at':self.now+300,'archive_id':'archive-test'}
    def old(self, name='system@aaa-bbb-ccc.journal'):
        p=self.src/name; p.write_bytes(b'opaque private log contents')
        os.utime(p,(self.now-MIN_AGE-60,)*2)
        return p
    def invoke(self, mode, policy=None, expected=None):
        r=Receipt()
        run(r,mode,policy or self.policy,expected,str(self.src),str(self.arc),self.now)
        return r
    def archive(self):
        return self.invoke('journal-archive').saved['journal-plan.json']
    def apply(self, plan):
        return self.invoke('journal-apply',{**self.policy,'plan':plan},plan['plan_sha256'])
    def test_archive_verified_before_removal_and_active_recent_preserved(self):
        p=self.old()
        active=self.old('system.journal'); recent=self.old('system@ddd-eee-fff.journal')
        os.utime(recent,(self.now,)*2)
        link=self.src/'system@abc-def-123.journal'; link.symlink_to(p)
        plan=self.archive()
        self.assertTrue(p.exists())
        self.assertEqual([p.name],[f['name'] for f in plan['files']])
        archived=self.arc/'archive-test'/p.name
        self.assertEqual(p.read_bytes(),archived.read_bytes())
        self.assertEqual(0o600,archived.stat().st_mode&0o777)
        self.assertEqual(0o700,archived.parent.stat().st_mode&0o777)
        r=self.apply(plan)
        self.assertFalse(p.exists()); self.assertTrue(active.exists()); self.assertTrue(recent.exists())
        self.assertEqual('journal_completed',r.events[-1][0])
        self.assertEqual(1,r.events[-1][1]['removed'])
        self.assertIn('guard-proposal.json',r.saved)
    def test_corrupt_or_missing_archive_aborts_before_any_unlink(self):
        for action in ('corrupt','missing','symlink'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as tmp:
                p=self.old(); plan=self.archive(); dest=self.arc/'archive-test'/p.name
                if action=='corrupt': dest.write_bytes(b'corrupt archive')
                else:
                    dest.unlink()
                    if action=='symlink': dest.symlink_to(p)
                with self.assertRaises((ValueError,OSError)): self.apply(plan)
                self.assertTrue(p.exists())
                import shutil; shutil.rmtree(self.arc/'archive-test')
    def test_source_changed_or_new_eligible_file_blocks_apply(self):
        p=self.old(); plan=self.archive(); p.write_bytes(b'changed source')
        with self.assertRaises(ValueError): self.apply(plan)
        self.assertTrue(p.exists())
    def test_no_authority_wrong_node_expired_and_path_traversal_rejected(self):
        p=self.old()
        for change in ({'node':'other'},{'approval_reference':''},{'approved_by':''},
                       {'reference_inventory_complete':False},{'expires_at':self.now},
                       {'archive_id':'../escape'}):
            with self.assertRaises(ValueError): self.invoke('journal-archive',{**self.policy,**change})
        self.assertTrue(p.exists()); self.assertEqual([],list(self.arc.iterdir()))
    def test_forged_manifest_and_hash_block_apply(self):
        p=self.old(); plan=self.archive()
        forged=copy.deepcopy(plan); forged['files'][0]['sha256']='0'*64
        with self.assertRaises(ValueError): self.apply(forged)
        self.assertTrue(p.exists())
    def test_reuse_archive_and_source_symlink_fail_closed(self):
        self.old(); self.archive()
        with self.assertRaises(FileExistsError): self.archive()
        alias=self.src.parent/'alias'; alias.symlink_to(self.src)
        with self.assertRaises(OSError):
            run(Receipt(),'journal-archive',self.policy,source=str(alias),archive=str(self.arc),now=self.now)

if __name__=='__main__': unittest.main()
