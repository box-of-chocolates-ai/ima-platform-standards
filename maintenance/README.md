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
