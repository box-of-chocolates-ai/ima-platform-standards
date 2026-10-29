# Sandbox source iteration

## Identify the actual development target

Separate four observations: guardrails reconciled, application runtime available,
source delivered, and application acceptance passed. Namespace creation, green
registration PRs, quotas or admission do not prove an application is running.
Check the named namespace and workload. A proposed sandbox stays proposed until
observed; never substitute another application's sandbox or infer a development
selector from production. Declare runtime names/selectors in a versioned contract.

Application owners supply the adapter and acceptance; the shared tooling owner
supplies transport and runtime contracts. Agree exact file ownership before
concurrent edits. Keep generic tooling in its verified owner, application source
and profiles in the application repo, and shared infrastructure in its owner.

## Separate the three loops

- Baseline provisioning: reviewed namespace guardrails, scoped access, and a
  qualified digest-pinned runtime with complete dependency/runtime fingerprints.
- Source iteration: sync admitted local working-tree bytes, including uncommitted
  edits, then restart or qualified hot reload in the isolated sandbox. Ordinary
  source edits need no commit, image publication or Argo sync.
- Production: reviewed immutable application/tool identities, image publication,
  guarded GitOps and the project's live proof. Dirty sandbox evidence is not
  production-build provenance or release qualification.

Changing dependency locks, runtime/build definitions, native/browser assets or
adapter entrypoints invalidates the baseline as applicable. Reject the mismatch
before upload or cluster mutation; rebuild and requalify instead of rewriting
the binding to make a check pass. The adapter must declare all relevant inputs;
a matching partial fingerprint cannot prove dependency equivalence.

## Use the smallest useful runtime

For a UI-only task, begin with an explicit fixture/static profile and synthetic
API responses. Admit individually named pages/scripts and reviewed referenced
assets. Do not upload the whole backend/tool tree or start the product executor
just to preview the UI. Static mode must serve the uploaded source directory,
not the image's stale baked-in application directory. Synthetic responses and
screenshots prove the UI contract only. Full application behavior needs its own
profile and acceptance.

Default to fresh processes and disposable state, no production PVC/data,
credentials or provider/court access. Preserve namespace-scoped sync, exec and
loopback port-forward; do not add node SSH authority. Validate explicit context,
namespace, workload ownership and runtime identity before writes. Missing
namespace, permissions or baseline fails closed, with no production fallback.

Source admission starts denied. Reject traversal and symlinks, bound files and
bytes, exclude ignored credentials/state and host dependencies, and verify
received bytes before releasing the application process. An extension or name
denylist is not a general secret scanner. Review application-specific allowlists.
Keep all Job/security/resource/deadline/cleanup requirements in force.

## Review access and replacement separately

A generic sync tool does not override an application's exec prohibition. Require
a reviewed sandbox-only transport scope before use; a review-reference string
records that decision but does not grant authority. Bind cluster server/public CA,
namespace UID, reviewed tool identity and qualified platform as well as context.
Check the named application container/image, not the first container in a list.

Repeated source runs need an owned stop/replacement contract with no overlap.
Preserve logs before deletion, guard the exact workload UID, confirm old processes
are gone and then create fresh state. Test destructive preconditions through the
actual installed client against a local fake API. A mocked argv assertion cannot
prove the server received the UID guard: an observed `kubectl delete --raw` call
discarded its DeleteOptions body. Reject uncertain outcomes without blind retry.

## Record what was actually tested

Keep tooling identity, baseline digest, application HEAD, scoped working-tree
patch hash, complete uploaded-content manifest (including admitted untracked
files), runtime/dependency fingerprints and Job/Pod UIDs. Hash only admitted
paths; do not inspect protected implementation to create a repository-wide hash.
HEAD alone cannot identify dirty source, and a tracked patch alone omits
untracked files. Save receipts in the application evidence store before expiry.

Persist intent before create and exact runtime identity before source delivery.
Uncertain create or upload requires reconciliation of that attempt, not blind
resubmission. A delivery acknowledgement proves bytes arrived, not HTTP readiness,
correct application output or a successful experiment. Preserve uncertainty.

Acceptance includes an uncommitted harmless edit changing rendered output without
a commit/publish/sync, dependency mismatch rejection, fresh disposable state,
complete source/baseline identity and unchanged production configuration. Separate
local receiver tests, mocked transport, hosted checks and real sandbox proof.
Do not claim future agent behavior is validated by adding a scenario rubric.
