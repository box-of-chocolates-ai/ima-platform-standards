"""Validate a cleanup proposal without deleting anything or granting authority."""
import argparse
import json
from pathlib import Path

DISPOSABLE = {"build-output", "image", "cache", "finished-job"}
PROTECTED = {"receipt", "ledger", "evaluation", "run-log", "branch", "workflow-run"}


def validate(plan):
    errors = []
    if plan.get("reference_inventory_complete") is not True:
        errors.append("reference inventory is incomplete")
    items = plan.get("items")
    if not isinstance(items, list) or not items:
        return errors + ["items must be a nonempty list"]
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("item must be an object")
            continue
        identity = item.get("id")
        if not isinstance(identity, str) or not identity or identity in seen:
            errors.append("missing or duplicate exact identity")
            continue
        seen.add(identity)
        kind = item.get("kind")
        if kind not in DISPOSABLE | PROTECTED:
            errors.append(f"{identity}: unknown kind")
            continue
        if not isinstance(item.get("references"), list):
            errors.append(f"{identity}: references must be inventoried")
            continue
        protected = kind in PROTECTED or bool(item["references"])
        # Inspect the actual contents of an artifact, not only its display name.
        contents = item.get("contains")
        if not isinstance(contents, list) or any(not isinstance(x, str) or x not in DISPOSABLE | PROTECTED for x in contents):
            errors.append(f"{identity}: contents inventory missing or unknown")
            continue
        protected |= bool(set(contents) & PROTECTED)
        if kind == "finished-job" and item.get("completed") is not True:
            errors.append(f"{identity}: job is not confirmed completed")
        if protected:
            decision = item.get("retention_decision", {})
            if not isinstance(decision, dict) or not (
                decision.get("id") == identity
                and decision.get("action") == "delete"
                and isinstance(decision.get("approved_by"), str)
                and bool(decision.get("approved_by", "").strip())
                and bool(decision.get("reason"))
                and bool(decision.get("approval_reference"))
                and bool(decision.get("loss_or_recovery_record"))
            ):
                errors.append(f"{identity}: explicit retention decision required")
        if kind == "image" and item.get("protected_digest_inventory_complete") is not True:
            errors.append(f"{identity}: protected digest inventory incomplete")
        if kind == "image" and item.get("deployed_or_rollback") is not False:
            errors.append(f"{identity}: deployed/rollback image cannot be cleaned")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text())
        errors = validate(plan) if isinstance(plan, dict) else ["plan must be an object"]
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    print(json.dumps({"valid": not errors, "errors": errors, "deletion_executed": False}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
