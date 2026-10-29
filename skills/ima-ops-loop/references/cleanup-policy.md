# Cleanup workflow

Use ima-platform-standards for the canonical workload/image requirements and retention guard. This reference defines the execution loop; it grants no live mutation, merge, node access or credential authority.

## Inventory and ownership

- Resolve the exact context, namespace, application owner, Argo source/revision and resource UIDs. Coordinate with an active owning thread before overlapping work. A namespace shared with another owner's apps is not a blanket cleanup scope.
- Record each candidate's terminal state, Pods, PVCs, receipts, pending intents and recovery references. Missing Pod logs or unverified receipts are a hold, not proof that the Job is disposable. Preserve suspended database recovery and qualification dependencies until explicitly released.
- Distinguish desired Jobs from source-retired Jobs awaiting pruning. Deleting a desired Job can recreate it; adding TTL alone can cause repeated execution. Retire obsolete resources through their owning GitOps source, preserving required flags, service accounts and storage. Do not enable application-wide pruning merely to remove an exact backlog.

## Preserve, guard, then delete

- Archive required Job/Pod metadata, complete available logs and durable receipts in an approved private evidence location; verify hashes before deletion. Redact secrets and keep sensitive evidence out of public source. Retain the archive independently of workload lifetime. A successful Job does not establish durable downstream evidence.
- Build an exact cleanup proposal and run the canonical retention guard. Protected evidence requires its own exact retention decision. Guard success is validation, not authorization. Existing user authorization need not be requested again when the exact action is already covered.
- Immediately before each write, recheck ownership, desired state, UID, terminal status and absence of active dependent Pods. Use UID and resourceVersion delete preconditions with narrowly scoped API access. Preserve intent, response and readback. A conflict or ambiguous response stops that item; inspect current state before any further action rather than repeating the delete against a replacement object.
- Verify target Job/Pod absence and unchanged protected workload/PVC identities and specifications. Scheduled Jobs can appear or expire concurrently: reconcile differences by owner UID and lifecycle state, retain them in the report, and do not silently waive changed protected resources.

## Prevent recurrence

- Update canonical, versioned producers, including manual/recovery factories and opt-in chart modes. Do not patch frozen release bundles. Apply the standard's positive TTL, CronJob history and concurrency requirements, with bounded, owned exceptions. Size retention for collection, outage and recovery windows.
- Persist results and identity-bound receipts outside Pod lifetime before normal expiry. Include crash/OOM collection and uncertain-intent reconciliation; an uploader that never ran is not persistence proof.
- Run the pinned checker on every enabled rendered mode and test generated manual Job manifests. A workflow reference alone does not prove coverage. Inspect actual admission actions: Warn/Audit permits requests; report scoped enforcement or daily retention alerts as proposals until deployed and verified. Enforcement changes require separate reviewed scope.
- Keep registry retention, node image GC and builder-cache cleanup separate. Preserve current/rollback digests and manifest closure; node GC settings remain with their owner. Never substitute broad prune for an exact inventory.
- Report Job/Pod counts separately from measured disk bytes. Use comparable before/after measurements and disclose concurrent activity. Image size reduction, registry deletion and node disk reclamation are different quantities.
