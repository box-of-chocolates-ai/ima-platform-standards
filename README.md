# Ima build and run standard

Start with [the project and agent guide](docs/agent-guide.md) for local/Ima entrypoints, skill installation, CI adoption and authority boundaries.

This public repository contains no workload inventory, credentials or customer data. It owns the standard and reusable checks for Ima projects across organizations. Consume a reviewed commit SHA, never a moving workflow reference. Application repos own their Dockerfiles, charts, size budgets and documented exceptions.

## GitOps placement

Keep application charts, values, databases, backup/recovery Jobs, schedules and image
pins in the owning application repo. Use the verified normal Ima app-of-apps for
registration, or the existing verified Trips-so deployment chain for Birdie/GolfTroop.
Treat mgmt-cluster edits as exceptions: verify current ownership and show why the
exact change cannot live in the application repo or normal app-of-apps. Record the
resource, evidence, necessity, minimum diff and validation in the plan or PR.
Existing mgmt placement, a runbook location or convenience does not establish necessity.

Shared operators, cluster-wide infrastructure and release of existing root registrations
may require mgmt. Such changes retain their own review and authority boundaries. If
necessity is unclear, continue read-only investigation and app-owned preparation but
make no mgmt or live mutation. Existing ownership stays intact until an explicitly
authorized staged transfer; never register a child under two parents.

## Workload lifecycle

Every Job, including migration hooks, qualification runs, canaries and manually generated lab runs, sets a positive `ttlSecondsAfterFinished`. Default to 86400 seconds after completion. Store receipts in the application evidence store before expiry. Longer retention needs a stated reason and must remain bounded.

Every CronJob explicitly sets `successfulJobsHistoryLimit`, `failedJobsHistoryLimit` and `concurrencyPolicy`, and its job template sets a TTL. Defaults are 2 successful, 3 failed and `Forbid`. A concurrency change is a behavior change requiring its own review.

Every application container and init container declares CPU and memory requests and limits, non-root execution, `allowPrivilegeEscalation: false`, and a read-only root filesystem. Mount narrowly scoped `emptyDir` volumes for required temporary writes. Long-running workers checkpoint and drain on termination within their explicit grace budget.

## Images and build context

Use a builder stage and a slim runtime that copies only built artifacts. Use distroless where native dependencies permit, and scratch only for static binaries. Pin bases by digest. Share a base only when its dependencies and release lifecycle genuinely match.

Start `.dockerignore` with `**`, then include only required paths. Never include `.git`, environment files, host `node_modules`, host `vendor`, storage logs/cache, credentials or customer test data. Re-exclude sensitive paths at the end when including a source tree. Dependency installation happens inside the builder. PHP runtime uses `composer install --no-dev`; Node assets use a throwaway stage. Playwright runtime installs only the Chromium headless shell and required native dependencies, with browser version tied to the Python/Node package.

Declare a byte budget for each built image and check it after build, per architecture. Initial ceilings: Python worker 350 MiB, PHP app 600 MiB, browser worker 900 MiB, static service 100 MiB. These are ceilings, not size targets. A larger image needs measured dependency costs, a reason and a reviewed explicit budget. Report registry compressed size and node-reported or Docker uncompressed size separately. Do not sum aliases as distinct images or shared layers as unique disk consumption.

## Registry retention and node storage

Plan a weekly GHCR retention pass keeping every deployed or rollback digest and the newest 20 per-commit versions. Resolve the protected set from all consuming GitOps pins and currently running image IDs, across architectures. Fail closed if enumeration is incomplete. Dry-run the deletion plan first. Never delete a protected digest through a different tag or multi-architecture child reference. Registry deletion and node image garbage collection are separate operations. No automatic deletion is enabled by this repository.

Node kubelet thresholds and image ages belong to Michael. Propose changes with disk and image inventory; do not run `docker prune`, `crictl rmi`, or change kubelet settings as a side effect of application work.

## Checks and adoption

Run `python -m unittest discover -s tests -v`. Install PyYAML, then run `python check.py --manifest rendered.yaml --dockerfile Dockerfile --ignore .dockerignore`. Render the chart for every enabled Job path, including hooks and one-offs. Use `--image IMAGE --max-image-bytes BYTES` after a real build. Source checks alone do not qualify a container.

The public reusable workflow accepts a repository-owned preparation script. That script renders Helm and invokes this pinned checker against the rendered manifests and images it actually built. It runs with read-only repository permissions and no secrets. Existing checks and image/runtime qualification remain required.

The cluster policy under `policies/` uses only Warn and Audit, never Deny. It is a proposal until Michael reviews and merges the cluster registration. CI verifies explicit fields before Kubernetes defaults obscure whether a caller supplied them. Admission can validate effective values but cannot reliably detect omission of fields that the API has already defaulted.

## References

- [TTL for finished Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/ttlafterfinished/)
- [CronJob history and concurrency](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Admission validation actions](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Kubelet image garbage collection](https://kubernetes.io/docs/concepts/architecture/garbage-collection/)

## Evidence retention and cleanup boundaries

Routine cleanup removes only regenerable build outputs, images, caches and finished Jobs, after protected-image and workload checks. Receipts, ledgers, evaluation state, report-referenced run logs, workflow runs containing evidence, and branches with open or referenced PRs are never deleted without an explicit retention decision. A successful build does not make its receipts disposable. Archive sanitized evidence and verify its hash before expiring a Job or artifact. Keep raw or sensitive material in its existing protected store, never in this public repository.

Run `python3 -B retention_guard.py cleanup-plan.json` before any cleanup proposal is approved. The checker only validates a proposal and never deletes anything. Each item needs an exact identity, kind, contents inventory and reference list; the plan must attest reference enumeration is complete. Protected items require an exact-item decision with approver, reason, approval reference and loss or recovery record. A valid plan still needs operational authority. This does not discover undeclared references or attest a caller's honesty. CI runs adversarial guard fixtures.

The versioned Codex skill source is [skills/ima-platform-standards](skills/ima-platform-standards). Install by copying this reviewed directory to your skills directory; local installation is a deployed copy, not the source of record. Skill decision scenarios are rubrics, not completed fresh-agent evaluations.
