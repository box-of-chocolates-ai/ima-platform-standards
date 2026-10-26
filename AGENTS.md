# Repository workflow

Read [docs/agent-guide.md](docs/agent-guide.md) for this project's ownership and conditional use on local and Ima agent hosts. Update the versioned skill source here before synchronizing installed copies. Do not assume another host has the workstation skill path or that a documentation link enables CI or runtime enforcement.

Use `/home/dylan/.codex/skills/ima-platform-standards/SKILL.md` when changing image or Kubernetes standards. Keep this public repository free of private workload inventories and credentials. Use feature branches and PRs for changes. Validate behavior using adversarial fixtures and rendered manifests. A green static check is not image or runtime qualification. Changes here do not authorize cluster enforcement, registry deletions or node cleanup.
