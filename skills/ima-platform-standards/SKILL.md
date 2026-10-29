---
name: ima-platform-standards
description: "Audit and fix Ima images and deployments: bounded Job cleanup, safe old-image retention, smaller images with functionality checks, and build/workload standards. Use for Dockerfiles, Helm, Jobs, CronJobs and image storage; skip unrelated application-only changes."
---

# Ima platform standards

The canonical standard and checks live at https://github.com/box-of-chocolates-ai/ima-platform-standards. Local checkout: `/garage/projects/ima-platform-standards`. Read its README before changing an Ima build or workload. Use the project-local Birdie workflow when present; this skill supplies checks, not a separate task lifecycle.

## Evidence preservation

Read [evidence-retention.md](references/evidence-retention.md) before any cleanup. Cleanup removes build outputs, images, caches and finished Jobs only. Receipts, ledgers, evaluation state, report-referenced run logs and branches with open or referenced PRs require a separate explicit retention decision before deletion. Run the canonical retention guard on the exact proposal; passing it grants no deletion authority. Preserve evidence before workload expiry.

Versioned source: `box-of-chocolates-ai/ima-platform-standards`, `skills/ima-platform-standards/`. This installed directory is a copy. Update and test the source, publish through a feature PR, then synchronize the installed copy.

## Tooling ownership and build inputs

Before placing reusable lab runners, builders or workflows, distinguish the tooling owner, application source owner and deployment owner. Application-owned charts do not imply that generic lab infrastructure belongs in the application repo. Verify the intended repository and existing interfaces; consuming an application as an input does not transfer ownership of the tooling. Preserve established placement until a migration is authorized.

For cross-repository builds, ports or recovery work, read [build-boundaries.md](references/build-boundaries.md). Require separate immutable tooling and application identities, validate admitted inputs before output creation or build side effects, and test rejection paths. Preserve recovered source as historical evidence; passing source tests does not qualify an image or runtime. These are builder contract requirements, not checks supplied by the current canonical static checker.

For development source sync or sandbox runtime readiness, read [sandbox-source-loop.md](references/sandbox-source-loop.md). Separate baseline provisioning from source iteration and production release. A qualified disposable sandbox may admit uncommitted allowlisted source with content receipts; this does not relax immutable inputs for production builds or qualification claims. Namespace guardrails, source delivery and changed application output are distinct evidence.

## GitOps ownership and thread priming

Prefer application-owned charts, values, image pins, schedules and database resources in the application repo. Use the normal `mwuhahaha/ima_kubernetes_robot` app-of-apps for ordinary Ima application registration. For Birdie/GolfTroop work, use the appropriate verified Trips-so repository and its existing deployment chain. Trips-so is an organization, not a guessed repository URL: resolve the actual source from project instructions and Argo sources before editing. These are GitOps ownership choices, not instructions to switch Kubernetes contexts.

Treat `mgmt-cluster` as an exception, not a deployment default. Before proposing any edit there, verify live Argo ownership and the existing application deployment chain, then establish why the exact change cannot be implemented in the application repo or normal app-of-apps. Existing placement in mgmt, a runbook stored there, convenience, or a working precedent is not sufficient justification. Application databases, backup/recovery Jobs, schedules, image pins and app-scoped access resources belong with the application wherever the existing platform contract permits.

Use mgmt only when an unavoidable dependency is owned there, such as a shared operator, cluster-wide storage/network configuration, or release of an existing root registration during an authorized transfer. Record the exact resource, ownership evidence, reason the application-owned route is insufficient, smallest required mgmt diff and validation in the plan or PR before mutation. Keep all remaining application work in its owner repo. Preserve shared and other owners' resources; a necessary shared change requires its own scoped authority and repository review. This skill grants no merge or cluster-write permission.

If necessity or ownership is uncertain, fail closed on mgmt and live mutations while continuing read-only investigation and app-owned preparation. Do not relocate existing resources implicitly to avoid mgmt: obtain migration authority, release the old parent with retention protections, verify release, and only then adopt under the new parent. Never register a child twice. Reading mgmt documentation and status is allowed for diagnosis; this restriction concerns placing resources and making changes there.

Prime future threads through applicable workspace/repo `AGENTS.md` with an explicit instruction to read this skill before Ima deployment, image or workload lifecycle changes. Keep it subordinate to the project-local Birdie coordinator. Instructions guide agents; enforce rendered manifest/build checks with the pinned canonical checker in CI. Do not claim instructions guarantee invocation, and do not add host hooks or auto-cleanup side effects merely to load a skill.

For existing deployments with accumulated Jobs, old images or oversized builds, read [remediation.md](references/remediation.md). Fix the owning templates and build pipeline so the problem does not recur; distinguish source changes from live cleanup.

For releases or self-audits, read [release-evidence.md](references/release-evidence.md). It separates exact-source CI, image qualification, deployed contracts and scheduled successor results.

Inspect current image/chart pins and runtime contracts first. Keep unrelated edits. All application Jobs, including one-offs and hooks, need a bounded positive TTL. CronJobs need explicit success/failure histories and concurrency policy, plus a TTL in the job template. Preserve existing schedules, concurrency and flags during image-only releases.

Use a digest-pinned multi-stage build with artifacts copied to a slim, non-root runtime. Build context starts denied (`**`) and includes only required paths. Re-exclude sensitive descendants of included source directories. Never copy host vendor, node_modules, .git, environment files or customer data. For Chromium-only workers, prefer Chromium headless shell when runtime qualification supports it; preserve other required engines, models and assets in multi-engine workloads. Every runtime image has a measured byte budget; distinguish compressed registry bytes from node or Docker image size.

Render all enabled chart modes, including migrations, recovery, qualification and canary Jobs. Run the pinned canonical checker against rendered YAML, Dockerfile and .dockerignore; run its image-budget check against the image actually built. Static checks do not replace entrypoint, storage, architecture and runtime qualification. Mount writable scratch space explicitly when adopting a read-only root filesystem.

Prefer the public pinned reusable workflow for cross-organization checks. Keep application-owned preparation scripts and budgets in each repo. Reference this skill from the repo's AGENTS.md. Report any justified exception with scope, reason, expiry and the check it replaces; never silently exclude a failing workload.

Order stable dependency and browser/model asset layers before frequently changing application code where dependencies permit. Use standard gzip registry compression by default; alternate formats require measured benefit and registry/runtime compatibility qualification. Compression does not reduce unpacked filesystem requirements or waive pull/unpack, coexistence and disk-reserve admission. See remediation guidance for measurements and exceptions. Static checks do not prove layer reuse, dependency minimality or compression compatibility.

Registry retention and kubelet image GC are distinct. Inventory first, preserve every deployed and rollback digest and multi-architecture child, and fail closed if the protected set is incomplete. A dry-run deletion plan is not deletion authority. Michael owns node GC settings. New admission policy starts Warn/Audit only, submitted through GitOps for review; never enable Deny or clean up live Jobs as a side effect.

Validate skill edits with `python3 /home/dylan/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/dylan/.codex/skills/ima-platform-standards`. Behavioral evaluation cases are in `evals/scenarios.json`; execute the canonical checker's adversarial suite as the technical verification, and record decision evaluation separately.
