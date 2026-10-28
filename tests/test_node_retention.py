import copy
import importlib.util
import tempfile
import time
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('node_retention', Path(__file__).parents[1] / 'maintenance/node_retention.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
REPO = 'registry.example/project/controller'
A, B, C = ['sha256:' + x * 64 for x in 'abc']


def image(identity=A, aliases=None, pinned=False):
    return {'id': identity, 'aliases': [REPO + '@' + identity] if aliases is None else aliases,
            'size': 123, 'pinned': pinned}


def policy():
    now = int(time.time())
    return {'version': 1, 'node': 'test-node', 'node_uid': 'test-uid', 'repository': REPO,
            'created_at': now, 'expires_at': now + 600, 'protected_digests': [B, C],
            'reference_inventory_complete': True, 'protected_digest_inventory_complete': True,
            'releases': {'current': {'digest': B, 'evidence': 'release-2'}, 'previous': {'digest': C, 'evidence': 'release-1'}},
            'source_snapshots': ['sha256:' + 'd' * 64], 'rollouts_held': True, 'approval_reference': 'reviewed-operation'}


class FakeRuntime:
    def __init__(self, images=None, containers=None):
        self.images = images or [image()]
        self.containers = containers or []
        self.calls = []
        self.snapshot_count = 0
        self.add_reference = False
        self.fail_remove = False
        self.fail_after_remove = False

    def snapshot(self):
        self.snapshot_count += 1
        refs = self.containers
        if self.add_reference and self.snapshot_count > 1:
            refs = [{'id': 'stopped', 'imageRef': A, 'image': REPO + '@' + A}]
        return copy.deepcopy(self.images), copy.deepcopy(refs)

    def call(self, *args):
        self.calls.append(args)
        if self.fail_remove:
            raise RuntimeError('private error must not enter receipt')
        self.images = [i for i in self.images if i['id'] != args[1]]
        if self.fail_after_remove:
            raise RuntimeError('timed out after successful server operation')


class RetentionTests(unittest.TestCase):
    def test_unowned_mixed_unknown_pinned_protected(self):
        for candidate in [image(aliases=[]), image(aliases=[REPO + ':old', 'registry.example/other/app:old']), image(pinned=True), image(B)]:
            self.assertEqual([], r.plan([candidate], [], policy())['candidates'])

    def test_tagged_digest_reference(self):
        alias = REPO + ':release@' + A
        self.assertEqual(REPO, r.alias_repo(alias))
        refs = r.container_inventory({'containers': [{'id': 'x', 'imageRef': alias, 'image': alias}]})
        self.assertEqual([], r.plan([image()], refs, policy())['candidates'])

    def test_digest_only_owned_image(self):
        self.assertEqual([image()], r.plan([image()], [], policy())['candidates'])

    def test_running_and_stopped_image_references(self):
        for reference in [A, REPO + '@' + A]:
            refs = [{'id': 'container', 'imageRef': reference, 'image': reference}]
            self.assertEqual([], r.plan([image()], refs, policy())['candidates'])

    def test_alias_reference(self):
        value = image(aliases=[REPO + ':old'])
        refs = [{'id': 'container', 'imageRef': B, 'image': REPO + ':old'}]
        self.assertEqual([], r.plan([value], refs, policy())['candidates'])

    def test_policy_rejections(self):
        changes = [{'expires_at': 1}, {'created_at': int(time.time()) + 100}, {'repository': 'registry.example/other/app'},
                   {'node': 'other-node'}, {'node_uid': ''}, {'protected_digests': []}, {'releases': {}},
                   {'reference_inventory_complete': False}, {'protected_digest_inventory_complete': False},
                   {'source_snapshots': []}, {'rollouts_held': False}, {'approval_reference': ''}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.validate_policy({**policy(), **change}, 'test-node', REPO)

    def test_missing_release_closure(self):
        p = policy()
        p['protected_digests'] = [B]
        with self.assertRaises(ValueError):
            r.validate_policy(p, 'test-node', REPO)

    def test_images_malformed(self):
        for raw in [{}, {'images': None}, {'images': [{'id': 'latest'}]}, {'images': [{'id': A, 'size': '1', 'repoTags': 'tag'}]},
                    {'images': [{'id': A, 'size': '1', 'repoTags': ['unknown']}]}, {'images': [{'id': A, 'size': '-1'}]},
                    {'images': [{'id': A, 'size': '1'}, {'id': A, 'size': '1'}]}]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                r.image_inventory(raw)

    def test_empty_inventory_is_complete(self):
        self.assertEqual([], r.image_inventory({'images': []}))
        self.assertEqual([], r.container_inventory({'containers': []}))

    def test_missing_container_references_abort(self):
        for raw in [{}, {'containers': [{'id': 'x'}]}, {'containers': [{'id': 'x', 'imageRef': A}]}]:
            with self.assertRaises(ValueError):
                r.container_inventory(raw)

    def test_inventory_changes_abort(self):
        runtime = r.Runtime()
        calls = iter([{'images': [{'id': A, 'size': '1'}]}, {'containers': []}, {'images': []}])
        runtime.call = lambda *args: next(calls)
        with self.assertRaises(ValueError):
            runtime.snapshot()

    def test_plan_hash_changes_with_alias_and_policy(self):
        p = policy()
        original = r.plan([image()], [], p)['plan_sha256']
        self.assertNotEqual(original, r.plan([image(aliases=[REPO + ':new'])], [], p)['plan_sha256'])
        p['approval_reference'] = 'another-operation'
        self.assertNotEqual(original, r.plan([image()], [], p)['plan_sha256'])

    def run_operation(self, runtime, mode='apply', expected=None, p=None):
        p = p or policy()
        expected = expected or r.plan(runtime.images, runtime.containers, p)['plan_sha256']
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        receipt = r.Receipt(Path(temporary.name) / 'run')
        r.execute(runtime, receipt, mode, p, expected, 'test-node', REPO)
        return receipt

    def test_inventory_and_plan_never_remove(self):
        for mode in ['inventory', 'plan']:
            runtime = FakeRuntime()
            self.run_operation(runtime, mode)
            self.assertEqual([], runtime.calls)

    def test_wrong_hash_never_removes(self):
        runtime = FakeRuntime()
        with self.assertRaises(ValueError):
            self.run_operation(runtime, expected='wrong')
        self.assertEqual([], runtime.calls)

    def test_new_reference_aborts_before_remove(self):
        runtime = FakeRuntime()
        runtime.add_reference = True
        with self.assertRaises(ValueError):
            self.run_operation(runtime)
        self.assertEqual([], runtime.calls)

    def test_apply_exact_image_and_receipts(self):
        runtime = FakeRuntime([image(), image(B)])
        receipt = self.run_operation(runtime)
        self.assertEqual([('rmi', A)], runtime.calls)
        self.assertTrue((receipt.path / 'inventory-after.json').exists())
        self.assertIn('remove_attempt', receipt.events.read_text())

    def test_first_failure_stops_and_reconciles(self):
        for completed in [False, True]:
            runtime = FakeRuntime([image(), image('sha256:' + 'e' * 64)])
            runtime.fail_remove = not completed
            runtime.fail_after_remove = completed
            with self.assertRaises(RuntimeError):
                self.run_operation(runtime)
            self.assertEqual(1, len(runtime.calls))
            self.assertEqual(3, runtime.snapshot_count)

    def test_run_id_cannot_overwrite_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                r.Receipt(directory)

    def test_no_arbitrary_commands(self):
        runtime = r.Runtime()
        for args in [('rmi', '--prune'), ('exec', 'x'), ('rmi', A, '--force'), ('images', '--verbose')]:
            with self.assertRaises(ValueError):
                runtime.call(*args)


if __name__ == '__main__':
    unittest.main()
