# Release evidence and self-audit

## Freeze the chain

Record source SHA, hosted check SHA, immutable image digest including architecture, chart revision, registration revision and previous working chart/image before release. A passing PR head does not prove the merge head passed. If CI compares a predecessor, fetch that exact commit before archiving it in a shallow checkout. Keep runtime flags and new opt-in paths at their authorized values.

For an image-only release, compare every existing CronJob before and after: schedule, suspend, concurrency, success/failure history, arguments and flags. Check both rendered source and deployed templates. API defaults can hide missing explicit fields, so a live manifest pass cannot replace source checks.

## Measure comparable builds

Compare predecessor and candidate built on the same runner, architecture and dependency resolution conditions. Distinguish compressed registry bytes, uncompressed image bytes and uniquely reclaimable node storage. Record transitive dependency drift if the resolver is not locked. Measure optimizations such as omitted Python bytecode rather than assuming savings. Reuse retained hosted image evidence with its exact SHA and date when local Docker is unavailable; label it retained evidence, not a new local build.

Use the project's dependency environment for tests. A missing SDK in system Python is an invocation failure, not proof of an application regression. Report focused tests, the full suite, hosted checks and runtime qualification separately. Repeat passing checks only after changed inputs, a new failure or a remaining concern warrants it.

## Prove successors and outcomes

Template pins alone do not establish execution. For each due scheduled lane, record the successor Job, actual pod imageID, completion and domain receipt. Job completion or exit zero does not establish successful delivery when the receipt records a conflict, deferral or preserved human edit. Report the exact disposition and unresolved work. Mark suspended or not-yet-due lanes unobserved; do not change schedules or trigger work merely to complete the audit.

Argo operation success, sync status and application health are separate observations. Compare transition times and resource health against the pre-release baseline. Prune-skipped counts alone do not identify the degraded resource; missing resource health leaves attribution unknown. Preserve recovery evidence and do not enable global prune as a health fix.

A named one-off Job still present in desired GitOps state may be recreated after TTL cleanup. Inspect hooks, sync policy and the runId/enable lifecycle. Persist receipts and retire the desired run through its owner when authorized. Do not omit TTL or repeatedly recreate qualification work to retain evidence.

## Close the audit honestly

Separate prepared fixes from deployed fixes, static compliance from runtime qualification, and documented retention plans from installed scheduled retention. Report scoped exceptions with reason and expiry. An allowlist regex check is not proof of complete Docker build-context exclusion semantics. Record skipped checks and the specific missing evidence. A self-audit grants no cleanup, deployment, enforcement or registry deletion authority.
