# Evidence is not a build output

Before cleanup, inventory exact artifact and run IDs, branch tips, PR references, report citations, ignored state and all consumers. Treat a workflow artifact as protected when it contains receipts even if its name says images. Treat a workflow-run deletion as deletion of its logs and artifacts. Unknown contents or incomplete references fail closed.

Routine cleanup covers regenerable build outputs, unprotected images, caches and finished Jobs only. Receipts, ledgers, evaluations, referenced run logs and branches with open or referenced PRs require an explicit retention decision naming each exact object, approver, reason, approval reference and verified recovery or acknowledged permanent-loss record. Branch merge status alone is not a retention decision. A dry-run guard is not permission.

Use the canonical `retention_guard.py` with an exact JSON proposal. It validates shape, protected contents, references, decisions, job completion and image protection. It performs no deletion and cannot discover references omitted by the caller. Keep its output with the decision. Before deleting a Job, capture sanitized logs and durable receipts and verify their hashes. Preserve private evidence in the owning protected store.

For recovery, retain deletion command metadata and provider readbacks, reconstruct refs from exact surviving commits, and hash recovered files. Record original evidence, recovered copies and new re-execution separately. Rebuilding cannot restore the original run's logs or prove that original execution. Never call a missing artifact recovered because its source still builds.
