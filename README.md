# Ima build and run standard

This public repository contains no workload inventory, credentials or customer data. It owns the standard and reusable checks for Ima projects across organizations. Consume a reviewed commit SHA, never a moving workflow reference. Application repos own their Dockerfiles, charts, size budgets and documented exceptions.

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
