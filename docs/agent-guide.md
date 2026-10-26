# Platform standards project guide

## Purpose and use

This public project owns Ima's build/workload standard, reusable checks, proposed admission policy and the source of the `ima-platform-standards` Codex skill. Start with [README.md](../README.md). Application repositories retain ownership of Dockerfiles, charts, images, budgets and exceptions.

Use this project when preparing or auditing images, Helm, Jobs, CronJobs, release evidence or retention. Keep ordinary application work in its project workflow. The skill supports the project-local Birdie coordinator where available; it does not replace that lifecycle.

## Agent entrypoints

| Context | Read or run |
| --- | --- |
| Local workstation | `/garage/projects/ima-platform-standards/README.md`; installed skill at `/home/dylan/.codex/skills/ima-platform-standards/SKILL.md` |
| Ima or another agent host | Reviewed checkout of this repo, `README.md`, then `skills/ima-platform-standards/SKILL.md`; do not assume workstation paths exist |
| Install or update the skill | Copy the complete versioned `skills/ima-platform-standards/` directory from a reviewed revision into that host's skill directory; preserve references and evals |
| CI | Pin a reviewed commit of the public reusable workflow/checker; application-owned preparation renders all enabled workload modes |
| Cleanup proposal | `python3 -B retention_guard.py cleanup-plan.json`; validation only, never deletion authority |
| Reusable lab work | [diagnostic-lab](https://github.com/box-of-chocolates-ai/diagnostic-lab), private; current execution core remains in BirdieSRE |

The source skill and retention guard are introduced in [PR #2](https://github.com/box-of-chocolates-ai/ima-platform-standards/pull/2). Until merged, they are candidate source on `fix/evidence-retention-and-skill-source`, not released main. Consumers must verify the reviewed source revision before adopting it. Local installation alone proves neither CI adoption nor invocation by another agent.

## Checks and limits

```sh
python3 -B -m unittest discover -s tests -v
python3 check.py --manifest rendered.yaml --dockerfile Dockerfile --ignore .dockerignore
```

The manifest check requires PyYAML and application-owned rendered inputs. Add `--image IMAGE --max-image-bytes BYTES` only against a real built image. Record source checks, image sizes, runtime qualification and scheduled successor results separately. Static checks do not attest container functionality.

Before side effects, resolve tooling, application and GitOps owners and immutable identities. Fail closed on uncertain protected-image sets or evidence references. Preserve receipts, ledgers, evaluation state, referenced run logs and PR branches unless an exact retention decision authorizes deletion. The guard validates supplied inventories; it does not discover omitted references.

Warn/Audit admission proposals do not enable enforcement. Nothing in these docs authorizes cluster writes, registry deletion, node cleanup or deployment. Keep private inventories, source snapshots, credentials and customer data out of this public repository.

## Maintenance

Change the standard, checks and versioned skill together when their contracts change. Test adversarial fixtures, publish through a feature PR, then synchronize installed copies from the reviewed revision. Keep consumers on pinned revisions until their own checks pass. The [Ima project index](https://github.com/mwuhahaha/ima_kubernetes_robot/tree/docs/reusable-projects-20261027/docs/projects) links this project without transferring resource ownership.
