# Remediate existing images and workloads

Use this when an existing Ima app accumulates finished Jobs, retains unnecessary images, or needs a smaller image without losing functionality. The canonical standards README remains the policy source; its budgets and defaults are starting points subject to measured application requirements.

## Establish scope and ownership

Read the app's instructions, release runbook, Dockerfiles, chart generators and active values. Identify the app repo, Argo registration repo, image publisher, runtime namespace, current digest and rollback digest. Follow Birdie when available. Change application-owned templates in the application repo; propose shared platform changes in their owning GitOps repo. Do not move app configuration to mgmt-cluster merely because it runs on Ima.

Collect a bounded read-only inventory: Job state/age/owner/TTL, CronJob histories, pending prune resources, node disk and inode headroom, and image references. Distinguish proposed setup, rendered configuration, deployed configuration and observed runtime. Old session reports are examples, not current inventory or permission.

## Keep completed Jobs bounded

- Fix every creation path: CronJob job templates, Helm/Argo hooks, manual generators, child Jobs, migration, recovery and qualification modes. Set a positive TTL and explicit CronJob success/failure histories. Preserve existing concurrency and schedules unless a behavior change is requested.
- Choose retention from the actual evidence/recovery window. A child result needed by the next four-hour controller pass cannot expire after one hour. Include start deadlines, controller outages and collection delay. Persist result records and receipts before cleanup. Record a bounded, reviewed exception where evidence cannot yet be safely expired.
- Retained restore/qualification Jobs may still be evidence dependencies. Do not delete them or turn on global Argo pruning to make health green. Inventory pending prunes separately.
- TTL is for completed Jobs. Bound stuck work with suitable active deadlines, retry limits and termination behavior after reviewing application semantics. A history limit is not a substitute for covering one-off and child Jobs.
- For existing backlog, produce an exact namespace/name/UID deletion list with terminal state, evidence location and reason each is safe. Re-read UIDs and state before separately authorized deletion. Protect active Jobs and unresolved recovery evidence. Setting TTL on old Jobs can make them immediately eligible for deletion and is itself a live cleanup action.

## Retain images safely

Treat registry retention, node runtime image GC and builder cache cleanup as separate systems. Deleting Jobs does not remove image layers; deleting registry tags does not reclaim node storage.

Build the protected digest set from all consumers, including other repos, running pods, desired GitOps pins, init containers, scheduled/one-off/hook jobs and rollback revisions. Protect multi-architecture indexes and children, and source images still required to reproduce or qualify builds. Keep at least the admitted current and previous rollback releases, plus anything else still referenced. Never decide deletion safety by age, tag or an apparently unused app alone. Stop if enumeration or ownership is incomplete.

Produce a dry-run candidate list and estimated unique reclaimable bytes with uncertainty stated. Configure a reviewed recurring retention mechanism where appropriate. Actual deletion needs authority for the exact store and scope. Node GC policy belongs to Michael; do not substitute blanket `docker system prune`, `crictl rmi --prune`, volume pruning or direct deletion under containerd storage. Disposable hosted-CI cleanup recipes are not Ima or workstation cleanup instructions.

## Make images smaller while preserving behavior

Measure the same architecture before and after: build context, layer history, compressed registry bytes and uncompressed image bytes. Attribute the largest costs before editing. Shared layers mean total reported image sizes are not unique node disk consumption.

Use deny-by-default context filters and selected COPY inputs. A `.dockerignore` reduces sent context; it does not remove files inherited from a base. Prefer multi-stage artifact-only runtime builds, runtime-only dependencies, cache removal in the creating layer, and ownership at COPY/install time instead of recursive chown of a large earlier layer. Preserve every engine, model, certificate, native library and tool required by the actual matrix. Chromium-only recommendations do not authorize removing Firefox or ASR from a multi-engine image.

For a lossless compaction candidate, compare final filesystem content/permissions/ownership/link targets and runtime configuration. Retain user, environment, entrypoint, command, workdir, signals and other supported image semantics; fail on unsupported metadata instead of silently dropping it. Layer flattening can reduce standalone bytes but loses layer sharing and may increase coexistence cost. This is an optional measured technique, not a universal build strategy.

Qualify baseline and candidate against the same entrypoint, architecture, non-root/read-only filesystem, writable mounts, asset checks and representative feature tests. For browser/ASR apps, check actual browser startup and inference as well as asset presence. Report untested capabilities explicitly. No-network tests prove offline runtime behavior, not accepted live CAPTCHA solves.

Before node adoption, budget pull/unpack peak, old/new coexistence, scratch and the existing disk reserve. Keep rollback available. Do not weaken admission floors to make a smaller image fit. Publish and deploy are separate evidence lanes; use the reviewed pinned-digest release path, verify runtime IDs and check functionality after rollout.

## Evidence and closure

Report the owning files changed, before/after byte measurements and denominator, retention windows, protected rollback set, commands actually run and their outcomes, deployed identity when applicable, and remaining capacity or qualification limits. Do not claim cleanup from a dry run, size savings from a Dockerfile edit, or runtime acceptance from CI alone.

Provenance: session `01a1321f-147e-7dc1-8bbd-bf19d89db191` documented finished Jobs lacking TTLs, seven-day node image-GC minimum age, proposed Warn/Audit admission and measured image-budget failures. Those observations motivated inventory-first remediation; they are historical, not current cluster state. Captcha Lab's subsequent lossless rebuild highlighted recursive-chown layer duplication, recovery-aware child TTLs and the need to preserve disk reserves during adoption.
