# Manual node image retention

This generic implementation is deployed separately from Holmes. Deployment and
private policies belong to the normal Ima GitOps owner, not this public repo.
No existing Holmes policy, node GC setting, automatic grant or release integration
is changed. Current scope is manual maintenance, not unattended weekly cleanup.

## Runtime boundary

The executable uses upstream crictl v1.36.0 with the published amd64 archive hash
`83855e114566a8a8c44c548d515670f51de3a5e1da8b2effb59870e2f10c25a3`.
Source: https://github.com/kubernetes-sigs/cri-tools/releases/tag/v1.36.0
Command documentation: https://github.com/kubernetes-sigs/cri-tools/blob/v1.36.0/docs/crictl.md
The runtime base and CRI artifact are pinned; no runtime package installation.

The Job mounts only its runtime socket, read-only policy and evidence PVC. It
needs UID 0 to open the node socket but no Linux capabilities, hostPID,
hostNetwork, privileged container or host root mount. Socket access itself is
runtime-wide administrator access: network policy, readOnlyRootFilesystem and
capability drops DO NOT constrain the socket API. The fixed image, reviewed
source, limited namespace writers and short Job lifetime are the boundary.
Do not claim the repository allowlist is a kernel-enforced runtime permission.
A namespace PSS exception is required for hostPath and root execution. Restrict
its purpose to this service; never give application runners this socket.

Only `images --output json`, `ps -a --output json`, and `rmi <full sha256 ID>`
can be invoked. All use the fixed socket and 60-second RPC timeout, a 75-second
child budget, 8 MiB per-stream output bound and 480-second overall budget.
No shell, force, prune, exec, host-directory deletion or log reads are supported.

## Policies and exact plan binding

Inventory mode reads every image and every running/stopped container. Policy
mode additionally requires an admitted node/repository, node UID, approval
reference, source-snapshot hashes, complete protected digest attestations,
current and previous successful release roots with evidence, rollout hold and
an expiring window of at most 24 hours. The deployment owner establishes these
from all consumers and registry manifest/config closure; a script cannot make
an incomplete operator inventory complete by asserting a boolean.

Unknown aliases, mixed repositories, pinned images, container references and
protected manifest/config digests exclude an image. Invalid inventories abort.
Images are read on both sides of the container-reference read. Dry-run hashes
bind the policy and exact candidates including aliases. Apply repeats planning,
requires the reviewed hash, invokes the canonical retention guard, then checks
each candidate against another fresh stable snapshot before serial removal.
CRI has no atomic conditional removal; this remains a snapshot-based guard.
Do not overlap maintenance and releases or image retagging.

Every run creates a new evidence directory exclusively. Policy, inventories,
plan, guard proposal and flushed event receipts persist on the PVC. An apply
also creates a PVC-wide exclusive directory lock; an unsuccessful apply leaves
it held for explicit operator reconciliation, never automatic retry. A new dry
run cannot authorize replay of an uncertain removal. Reconcile inventory and
record an operator recovery decision before clearing that exact stale lock.
The first removal error stops and records an independently observed absent,
still_present or unavailable state. No raw runtime stderr enters logs.

The normalized image/reference inventory is also emitted as a structured event
for operator retrieval after the Job exits. It contains no container environment,
mount configuration, runtime stderr or application logs. Treat these logs as
private workload metadata; do not publish them in this public source repo.

TTL cleanup must follow evidence verification. Do not place historical receipts
in ConfigMaps. Filesystem availableBytes before/after is the reclamation metric;
image size sums include shared layers and are not a space-savings claim.

## Verification

```
python3 -B -m unittest discover -s tests -v
```

CI additionally builds the image, checks its actual uncompressed byte budget,
and runs Python entrypoint and crictl version checks with no network, read-only
root filesystem and no capabilities. These checks do not attest host socket
access. Deployment must qualify inventory-only before explicit apply.

## APT download cache

`cache-plan` inventories only regular, single-link `.deb` files at least seven
 days old in the fixed `/host-apt-archives` mount. `cache-apply` requires an
exact reviewed plan hash, node, expiring approval and complete reference
attestation. It reruns the canonical retention guard and rechecks file metadata
before each unlink. No file contents are read. Names, device/inode, size,
allocated blocks and modification/change timestamps bind the plan; these are
metadata identities, not content hashes. Non-APT writers do not honor its lock,
so maintenance must not overlap other cache writers.

Both modes hold APT's POSIX record lock (not BSD flock), without creating or
removing its lock file. Symlinks, directories, hardlinks, young downloads,
partial downloads and other file types are excluded. The Job for this mode
mounts only the exact APT archive directory and receipts, with no runtime
socket, host root, host process access or package database. It removes cached
downloads only, never installed packages, configuration or journals. Failures
stop without retry and preserve receipts. Available-byte deltas, rather than
file-size sums, measure reclamation. Deployment and private plans remain in
the GitOps owner; this public source contains no node inventories.

Nanosecond timestamps are decimal strings so Helm/JSON numeric conversion cannot
round identities above 2^53. Rendered policy round-trip tests belong to deployment.

## Old system journal archival

`journal-archive` copies only archived `.journal` files at least seven days old
from the exact mounted machine journal directory. It does not parse or print log
contents. Active journals, recent files, symlinks and hardlinks are excluded.
A separate retained private archive PVC receives opaque copies in exclusive
0700 directories with 0600 files. Copy, fsync and full SHA-256 readback precede
publishing the manifest. Partial archives are retained as failed evidence.

`journal-apply` binds an expiring operator approval and exact reviewed manifest.
It verifies every recovery copy before removing any original, checks source
metadata again before each unlink, and uses the canonical retention guard with
an explicit per-file recovery record. The archive mount is read-only for apply;
only the exact source directory is writable. Neither mode mounts a runtime
socket, host root or secrets, or invokes a shell. PVC locking serializes modes;
failures retain the lock for explicit reconciliation rather than automatic retry.
No automatic retention of the private archive is configured. Preserve it until
an independently authorized retention decision permits removal.

## Separate scoped seccomp provisioning

`seccomp_profile.py` is a separate operation, not a node-retention mode. It admits
only the reviewed Patchright amd64/no-capabilities OCI bytes. Application code
never receives its host mount or UID 0. Deployment and node identity bindings
belong to the normal Ima GitOps repository, not mgmt-cluster.

The proposed one-shot Job mounts only `/var/lib/kubelet/seccomp/captcha-lab` at
`/host-seccomp`, its immutable configuration at `/profile`, and the existing
private maintenance receipt PVC at `/receipts`. It needs UID 0 for the root-owned
profile directory but no Linux capabilities, privileged mode, runtime socket,
host shell/namespaces, network, API token, or broad host-root mount. It changes no
kubelet flags, runtime defaults, AppArmor profiles or security admission policies.

The expiring request binds node name and expected node UID, run ID and profile
hash. The caller must independently verify actual node UID before activation and
after collection; a downward API node name is not a node-UID attestation. The
installer persists intent before writes, publishes complete bytes without
replacement, checks readback, and persists a completion receipt. Existing exact
read-only bytes can be adopted in a new run without rewriting them. A repeated
run ID, unfinished intent, unsafe directory, symlink/hardlink or mismatched file
stops execution. A failed/uncertain run is never blindly retried.

Provisioning is not native qualification. Preserve original browser failures and
require an isolated all-network-denied native namespace probe followed by actual
sandboxed browser controls. A denied AppArmor boundary requires a separate scoped
review, not `Unconfined`. No profile removal or overwrite command is supplied;
rollback disables future consumers and retains the installed inert file until
an explicit no-consumer removal decision. Disable the desired one-shot operation
before TTL so Argo cannot recreate it. Archive request, rendered manifest,
actual Job/Pod/node/imageID, intent and receipt before expiry.
