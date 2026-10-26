# Tooling ownership and revision-bound build inputs

## Placement before implementation

Resolve three owners explicitly: reusable tooling, application source/scenarios, and GitOps deployment. Inspect project instructions, actual repository origins and existing execution interfaces. Generic runners, build orchestration and environment adapters belong with their verified tooling owner; application instrumentation, factories and project scenarios remain project-owned. Do not create a guessed remote, duplicate an execution core, or relocate resources because a runbook or application checkout is nearby. Uncertain ownership blocks external mutations while local investigation continues.

## Independent identities and admission

A cross-repository builder must accept the application repository and exact commit as explicit inputs. It must separately identify the tooling commit or content-addressed bundle, including recipes and source-export policy. Never infer application source from the builder's own checkout or use one revision argument for both. A repository origin check confirms configured identity, not authenticity of arbitrary Git objects; use trusted checkouts or independently verified source provenance for release.

Validate all admission conditions before creating output, exporting source, invoking Docker, publishing, or starting workloads:

- admitted project/source profile and repository identity;
- exact application commit exists and matches the requested identity;
- tooling identity matches the actual scripts, recipes and policy;
- selected Git entries are allowlisted regular blobs, with required files present;
- base images are immutable and output is fresh, with no unsafe overwrite.

Fail closed with a bounded error category on mismatch, unknown identity or unsupported source profile. Export committed Git objects, never dirty working files or an unrestricted directory copy. Recheck identities at consumption or build from an immutable snapshot so concurrent edits cannot invalidate admission. Keep secrets and customer data outside contexts and diagnostics.

Record application repository/commit, tooling identity, export-profile identity, context hash and resulting image digest in receipts. Carry distinct identities into image metadata without replacing the deployment digest pin. A local content bundle is acceptable for local qualification; it is not an exact-source hosted release attestation.

## Recovery and verification

Keep a recovered snapshot immutable with its source revision, file hashes and byte counts. Port in a separate directory or isolated worktree. Reconcile old workflows with current owners, triggers, entrypoints and interfaces before reuse. Deleted artifacts or run logs are unavailable evidence; historical links do not establish current qualification.

Builder tests must exercise distinct application/tooling inputs, wrong repository, missing or floating commit, tooling drift, missing required files, selected symlinks and dirty-source exclusion. Assert rejected inputs cause neither output creation nor Docker/publish calls. Use a synthetic Git fixture and intercepted external tools; do not trigger a real build merely to test rejection. Include a valid external-source control proving the application and tooling identities survive into the build command and receipt.

Report source tests, source admission, context export, actual build, image qualification, deployment and runtime behavior separately. A successful source-only port still needs image functionality, platform checks, exact entrypoints, storage/network controls and recovery qualification before release. The canonical static checker does not currently enforce repository placement or multi-source identity; implement these guards and tests in the owning builder. Instructions and scenario rubrics alone are not mechanical enforcement.
