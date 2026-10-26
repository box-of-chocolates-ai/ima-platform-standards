import copy
import unittest
from retention_guard import validate


class RetentionTests(unittest.TestCase):
    def plan(self, kind="build-output"):
        return {"reference_inventory_complete": True, "items": [
            {"id": "artifact:123", "kind": kind, "references": [], "contains": [kind]}]}

    def test_disposable(self):
        self.assertEqual(validate(self.plan()), [])

    def test_incomplete_inventory(self):
        p = self.plan(); p["reference_inventory_complete"] = False
        self.assertTrue(validate(p))

    def test_protected_types(self):
        for kind in ("receipt", "ledger", "evaluation", "run-log", "branch", "workflow-run"):
            with self.subTest(kind=kind): self.assertTrue(validate(self.plan(kind)))

    def test_disguised_artifact(self):
        p = self.plan(); p["items"][0]["contains"].append("receipt")
        self.assertTrue(validate(p))

    def test_report_reference(self):
        p = self.plan(); p["items"][0]["references"] = ["report:abc"]
        self.assertTrue(validate(p))

    def test_explicit_exact_decision(self):
        p = self.plan("branch")
        p["items"][0]["retention_decision"] = {
            "id": "artifact:123", "action": "delete", "approved_by": "operator",
            "reason": "archived", "approval_reference": "decision:123",
            "loss_or_recovery_record": "archive:sha256:abc"}
        self.assertEqual(validate(p), [])
        q = copy.deepcopy(p); q["items"][0]["retention_decision"]["id"] = "other"
        self.assertTrue(validate(q))

    def test_running_job(self):
        self.assertTrue(validate(self.plan("finished-job")))

    def test_image_requires_protected_inventory(self):
        p = self.plan("image")
        self.assertTrue(validate(p))
        p["items"][0].update(protected_digest_inventory_complete=True, deployed_or_rollback=False)
        self.assertEqual(validate(p), [])

    def test_missing_and_unknown_contents(self):
        p = self.plan(); del p["items"][0]["contains"]
        self.assertTrue(validate(p))
        p["items"][0]["contains"] = ["unknown"]
        self.assertTrue(validate(p))

    def test_duplicate_identity(self):
        p = self.plan(); p["items"].append(copy.deepcopy(p["items"][0]))
        self.assertTrue(validate(p))
