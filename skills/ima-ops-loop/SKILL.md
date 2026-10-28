---
name: ima-ops-loop
description: How a turn of work runs for anything on the Ima Kubernetes cluster, including apps added later. Use at the start of any task that builds, deploys, releases, tests against, observes, qualifies, benchmarks or changes workloads on Ima, or when unsure whether a task touches Ima. Pairs with ima-platform-standards.
---

# Ima ops loop

How Dylan wants work on the Ima cluster to run. NEVER use long dashes (em or en dash). ima-platform-standards defines what builds and
workloads must meet; this skill defines how a turn of work runs. Where they overlap, ima-platform-standards wins. If a project has its
own coordinator workflow (for example Birdie), follow that workflow's lifecycle and apply these rules inside it; flag any conflict.

## 1. Is this Ima work? (decide at the start, every task)
It is Ima work if any of these is true:
- The repo, or its chart, is registered as an Argo Application in mwuhahaha/ima_kubernetes_robot, a verified Trips-so deployment
  chain, or a box-of-chocolates-ai repo that Argo on Ima watches.
- The task needs the Ima kube context, an Ima namespace, Ima nodes, or Ima egress.
- The repo's AGENTS.md has an "Ima project profile".
- The task builds an image or chart that Ima will run.
Check with read-only steps (repo files, Argo Applications, namespaces). If it is Ima work, say so in one line at the start. If it is
unclear, treat it as Ima work and say why it is unclear. If it is not Ima work, do not apply this skill.

## 2. Project profile
Look for an "Ima project profile" in the repo's AGENTS.md:
- App and namespace(s); GitOps owner repo and Argo Application.
- Dev environment for iteration (namespace or sandbox), or "none" with the fallback.
- What counts as live proof (for example a real product search from Dylan's session).
- Project-specific safety rules.
If there is no profile, derive one from the repo and the cluster, use it, and propose it as a small AGENTS.md PR in that repo. If the
app has no dev environment, say so and propose a fallback (a branch deploy into a sandbox namespace, a canary, or a guarded release
with extra verification) before starting.

## 3. When this method does not fit
If any rule here looks wrong for the current task (no dev environment, an emergency fix that cannot wait for dev, the release cap
would block a needed fix), tell Dylan at the start with the reason and what you would do instead, before deviating. Never quietly
ignore a rule, and never let a rule produce an obviously bad outcome without flagging it. Safety rules are not up for deviation
without Dylan's explicit yes.

## 4. Where to iterate
- Use the project's verified isolated dev runtime. Provision its baseline and access separately from ordinary source iteration. Where a qualified source-sync contract exists, sync allowlisted working-tree edits and restart or hot reload there without a commit, image publication or Argo sync per edit. Dependency/runtime input changes require a rebuilt and requalified baseline.
- Guardrails or registration alone do not prove runtime readiness. Declare the sandbox identity explicitly, preserve disposable state and source-content receipts, and prove changed application output. Start UI work with a fixture/static profile and synthetic API responses; full application mode is separate. Missing identity or readiness fails closed, with no other-project or production fallback. Apply ima-platform-standards' sandbox source-loop reference for detailed admission and evidence requirements.
- Production gets one guarded release per app, only after the change works in dev.
- Dev experiments do not need production release ceremony. Keep that for production.

## 5. Caps (per turn)
- At most 2 production releases per turn in total, unless Dylan says otherwise.
- At most 3 dev attempts per item.
- If the same approach failed twice, change the method before the third attempt, or ask Dylan whether a two-minute manual step from
  him would unblock it.
- When an item hits its cap: write what was learned and exactly what the next attempt needs, park it, move to the next item.

## 6. When to stop
- Stop when every item is shipped and verified live, parked under the cap, or truly blocked on something only Dylan or an outside
  party can provide.
- A green, reviewed change that is not live is not done.
- Never stop with a release half done; finish or recover it first.
- No wall-clock budgets. Report once, at the end.

## 7. Always keep (safety)
- Backup and integrity check before a release of anything with state; one writer at a time for single-writer stores.
- Disk headroom gate, never waived; rollback point recorded before the release.
- Never touch other apps' or other owners' resources or images. Respect ima-platform-standards on mgmt-cluster changes and node GC.
- No secrets, cookies, tokens or personal data in reports, PRs or chat.
- Live proofs through the real product path the profile names.
- Run everything yourself; never hand Dylan commands to run.
- Plus the project profile's own safety rules.

## 8. Measuring
- Before and after numbers for every speed or size claim, measured the same way (OTel/Tempo spans where available).
- Separate network time, waits, parsing and startup.

## 9. Report (short, one per turn)
- Ima detection result and profile used (and any profile PR proposed).
- What is live (images, nodes) with the profile's live proof.
- Each item: shipped, parked (with what it needs) or blocked (on whom).
- Production releases used out of 2.
- End with: $xclip full handoff/report data when finished.
