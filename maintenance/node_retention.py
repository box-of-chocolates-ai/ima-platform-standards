"""Manual, exact-repository CRI image retention. No scheduling or host shell."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from datetime import datetime, timezone

DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
REPOSITORY = re.compile(r"[a-z0-9.-]+(?::[0-9]+)?/[a-z0-9._/-]+\Z")
ENDPOINT = "unix:///runtime/containerd.sock"
MAX_BYTES = 8 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    require(isinstance(value, str) and DIGEST.fullmatch(value), "invalid immutable digest")
    return value


def alias_repo(value):
    require(isinstance(value, str) and value and not any(c.isspace() for c in value), "invalid image alias")
    if "@" in value:
        repo, suffix = value.rsplit("@", 1)
        sha(suffix)
        # Kubernetes accepts repository:tag@digest; the tag is not ownership.
        head, slash, tail = repo.rpartition("/")
        if ":" in tail:
            tail, _, tag = tail.rpartition(":")
            require(bool(tag), "invalid tag before digest")
            repo = head + slash + tail
    else:
        repo, sep, tag = value.rpartition(":")
        require(sep and tag and "/" in repo, "image alias must have repository and tag or digest")
    require(REPOSITORY.fullmatch(repo), "invalid repository")
    return repo


def image_inventory(raw):
    require(isinstance(raw, dict) and isinstance(raw.get("images"), list), "incomplete image inventory")
    out = []
    for row in raw["images"]:
        require(isinstance(row, dict), "invalid image record")
        identity = sha(row.get("id"))
        aliases = []
        for field in ("repoTags", "repoDigests"):
            values = row.get(field, [])
            require(isinstance(values, list), "invalid aliases")
            for value in values:
                alias_repo(value)
                aliases.append(value)
        size = row.get("size")
        require(isinstance(size, (str, int)) and str(size).isdigit(), "invalid image size")
        require(isinstance(row.get("pinned", False), bool), "invalid pinned field")
        out.append({"id": identity, "aliases": sorted(set(aliases)), "size": int(size), "pinned": row.get("pinned", False)})
    require(len({r["id"] for r in out}) == len(out), "duplicate image identity")
    return sorted(out, key=lambda x: x["id"])


def container_inventory(raw):
    require(isinstance(raw, dict) and isinstance(raw.get("containers"), list), "incomplete container inventory")
    out = []
    for row in raw["containers"]:
        require(isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"], "invalid container identity")
        ref = row.get("imageRef")
        require(isinstance(ref, str) and ref, "missing running/stopped container image reference")
        image = row.get("image", {}).get("image")
        require(isinstance(image, str) and image, "missing container image")
        for value in (ref, image):
            if not DIGEST.fullmatch(value):
                alias_repo(value)
        out.append({"id": row["id"], "imageRef": ref, "image": image})
    require(len({r["id"] for r in out}) == len(out), "duplicate container identity")
    return sorted(out, key=lambda x: x["id"])


def validate_policy(policy, node, repository, now=None):
    require(isinstance(policy, dict) and policy.get("version") == 1, "invalid policy version")
    require(REPOSITORY.fullmatch(repository) and policy.get("repository") == repository, "repository not admitted")
    require(node and policy.get("node") == node and policy.get("node_uid"), "node not admitted")
    now = time.time() if now is None else now
    created, expires = policy.get("created_at"), policy.get("expires_at")
    require(type(created) is int and type(expires) is int and created <= now + 30 and created < expires <= created + 86400 and now < expires, "expired or invalid policy window")
    require(policy.get("reference_inventory_complete") is True and policy.get("protected_digest_inventory_complete") is True, "incomplete protected set")
    protected = policy.get("protected_digests")
    require(isinstance(protected, list) and protected, "empty protected set")
    for value in protected:
        sha(value)
    releases = policy.get("releases")
    require(isinstance(releases, dict) and set(releases) == {"current", "previous"}, "current and previous successful releases required")
    for release in releases.values():
        require(isinstance(release, dict) and release.get("evidence"), "release evidence required")
        require(sha(release.get("digest")) in protected, "release not protected")
    require(isinstance(policy.get("source_snapshots"), list) and policy["source_snapshots"], "source snapshots required")
    for snapshot in policy["source_snapshots"]:
        sha(snapshot)
    require(policy.get("rollouts_held") is True and policy.get("approval_reference"), "rollout hold and cleanup authority required")
    return policy


def plan(images, containers, policy):
    protected = set(policy["protected_digests"])
    refs = {r[k] for r in containers for k in ("imageRef", "image")}
    refs |= {value.rsplit("@", 1)[1] for value in refs if "@" in value}
    candidates, excluded = [], []
    for image in images:
        aliases = image["aliases"]
        ids = {image["id"]} | {v.rsplit("@", 1)[1] for v in aliases if "@" in v}
        reasons = []
        if not aliases or any(alias_repo(a) != policy["repository"] for a in aliases):
            reasons.append("unowned_or_unknown_alias")
        if image["pinned"]:
            reasons.append("runtime_pinned")
        if ids & protected:
            reasons.append("protected_release_or_workload")
        if refs & (ids | set(aliases)):
            reasons.append("running_or_stopped_container")
        if reasons:
            excluded.append({"id": image["id"], "reasons": reasons})
        else:
            candidates.append(image)
    proposal = {"version": 1, "policy_sha256": digest(policy), "candidates": candidates}
    return {**proposal, "plan_sha256": digest(proposal), "excluded": excluded,
            "reference_inventory_complete": True, "reported_size_is_not_reclaimable_bytes": True}


class Runtime:
    def __init__(self):
        self.deadline = time.monotonic() + 480

    def call(self, *args):
        require(args in (("images", "--output", "json"), ("ps", "-a", "--output", "json")) or
                len(args) == 2 and args[0] == "rmi" and DIGEST.fullmatch(args[1]), "host command not allowed")
        remaining = min(75, self.deadline - time.monotonic())
        require(remaining > 0, "run deadline exceeded")
        # Files bound memory use even when the subprocess produces excessive output.
        import tempfile
        import resource
        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            proc = subprocess.run(["/usr/local/bin/crictl", "--runtime-endpoint", ENDPOINT,
                "--image-endpoint", ENDPOINT, "--timeout", "60s", *args], stdout=stdout, stderr=stderr,
                timeout=remaining, check=False, preexec_fn=limits)
            require(proc.returncode == 0, "runtime command failed; outcome may be uncertain")
            require(stdout.tell() < MAX_BYTES and stderr.tell() < MAX_BYTES, "runtime output limit")
            stdout.seek(0)
            return json.loads(stdout.read()) if args[0] != "rmi" else None

    def snapshot(self):
        first = image_inventory(self.call("images", "--output", "json"))
        containers = container_inventory(self.call("ps", "-a", "--output", "json"))
        second = image_inventory(self.call("images", "--output", "json"))
        require(first == second, "image inventory changed during reference read")
        return first, containers


class Receipt:
    def __init__(self, directory):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=False)
        self.events = self.path / "events.jsonl"

    def emit(self, event, **data):
        record = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **data}
        with self.events.open("a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        print(json.dumps(record, sort_keys=True), flush=True)

    def save(self, name, data):
        target = self.path / name
        with target.open("x") as f:
            json.dump(data, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())


def execute(runtime, receipt, mode, policy=None, expected=None, node=None, repository=None):
    images, containers = runtime.snapshot()
    receipt.save("inventory.json", {"images": images, "containers": containers})
    receipt.emit("inventory_saved", images=len(images), containers=len(containers))
    if mode == "inventory":
        return
    validate_policy(policy, node, repository)
    result = plan(images, containers, policy)
    receipt.save("plan.json", result)
    receipt.emit("plan", **result)
    if mode != "apply":
        return
    require(isinstance(expected, str) and expected == result["plan_sha256"], "reviewed plan changed")
    # The canonical guard validates the exact deletion proposal as well as policy checks.
    from retention_guard import validate
    guard = {"reference_inventory_complete": True, "items": [
        {"id": i["id"], "kind": "image", "contains": ["image"], "references": [],
         "protected_digest_inventory_complete": True, "deployed_or_rollback": False}
        for i in result["candidates"]]}
    if result["candidates"]:
        require(not validate(guard), "canonical retention guard rejected proposal")
    receipt.save("guard-proposal.json", guard)
    receipt.save("policy.json", policy)
    for candidate in result["candidates"]:
        validate_policy(policy, node, repository)
        current_images, current_containers = runtime.snapshot()
        eligible = plan(current_images, current_containers, policy)["candidates"]
        require(candidate in eligible, "candidate acquired a reference, alias, or protection")
        # No new eligible image can be added to this frozen approved list.
        receipt.emit("remove_attempt", image_id=candidate["id"])
        try:
            runtime.call("rmi", candidate["id"])
        except Exception:
            state = "unavailable"
            try:
                remaining, _ = runtime.snapshot()
                state = "still_present" if any(i["id"] == candidate["id"] for i in remaining) else "absent"
            except Exception:
                pass
            receipt.emit("remove_failed_or_unknown", image_id=candidate["id"], reconciliation=state, requires_fresh_plan=True)
            raise
        receipt.emit("remove_returned_success", image_id=candidate["id"])
    final_images, final_containers = runtime.snapshot()
    require(not ({i["id"] for i in final_images} & {i["id"] for i in result["candidates"]}), "removed image still present")
    receipt.save("inventory-after.json", {"images": final_images, "containers": final_containers})
    receipt.emit("completed", removed=len(result["candidates"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("inventory", "plan", "apply"), required=True)
    parser.add_argument("--policy", type=Path, default=Path("/policy/policy.json"))
    parser.add_argument("--expect-plan")
    args = parser.parse_args()
    node, repository = os.environ["ADMITTED_NODE"], os.environ["ADMITTED_REPOSITORY"]
    require(os.environ["NODE_NAME"] == node, "pod placed on unapproved node")
    run_id = os.environ["RUN_ID"]
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", run_id), "invalid run id")
    receipt = Receipt(Path("/receipts") / run_id)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError()))
    try:
        policy = json.loads(args.policy.read_text()) if args.mode != "inventory" else None
        lock = Path("/receipts/.apply-lock")
        if args.mode == "apply":
            lock.mkdir(exist_ok=False)
            receipt.emit("apply_lock_acquired")
        execute(Runtime(), receipt, args.mode, policy, args.expect_plan, node, repository)
        if args.mode == "apply":
            lock.rmdir()
    except Exception as exc:
        # Arbitrary subprocess stderr, paths and exception messages are never logged.
        receipt.emit("aborted", category=type(exc).__name__, requires_fresh_plan=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
