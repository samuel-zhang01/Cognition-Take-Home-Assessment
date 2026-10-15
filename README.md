# Cognition take-home: shared internal tools

Research and planning for a two-hour Devin Cloud prototype. **The prototype has not been built yet.** This repository currently contains the evidence, proposed design and handoff context; there are no application run commands to claim or follow yet.

The assessment concerns a fintech with about 60 engineers, $250K/year in internal-platform spending, three existing tools and at least ten planned tools. The question is whether Devin-assisted development produces enough useful customization and savings to justify engineering ownership.

## Continue with Devin

Copy the [standalone Devin prompt](<2. Planning/2.devin-handoff-prompt.md>) into a Devin Cloud session connected to this repository. It includes the scope, time checkpoints, checks and reporting requirements.

- [Current prototype plan](<2. Planning/0.prototype-plan.md>): three thin workflows, one shared foundation, hard 120-minute build cap.
- [Decision log](<2. Planning/1.decision-log.md>): who decided what, when, why and which older proposals were superseded.
- [Research and economics](<1. Research/0.research.md>): sourced platform comparison, pricing, ownership costs and customer KPIs.
- [Insurance proxy and Code Apps comparison](<1. Research/evidence/insurance-proxy-and-code-apps.md>): domain boundaries and the hybrid alternative.
- [Assessment brief](./_instructions.md): source requirements and deliverables. Its embedded TODO is context, not a fresh instruction to repeat completed research.

## Intended demonstration

| Assessment tool | Insurance-informed proxy | Small working slice |
| --- | --- | --- |
| KYC review queue | Fictional insurer/counterparty review | Inspect synthetic evidence; approve/reject with a reason. |
| Refunds dashboard | Claim/payment request | Inspect linked context; record a simulated approval. |
| Feature-flag admin | Sandbox configuration | Change a boolean with a reason. |

The portal shares demo sign-in, server-side permissions, persistent data and audit history. Insurance is Samuel's experience-based proof-of-concept proxy; it does not establish the fintech's actual requirements or complete KYC compliance. All example entities and rating/payout information are synthetic. No payment is executed.

Engineers add modules with Devin. Non-engineers can request changes with Devin, followed by engineering code review before release. The demonstration uses the repository workflow, without building an additional AI editor. Power Apps Code Apps remains a documentation-backed comparison in this run.

## Evidence and handover

Evaluate avoidable ownership cost, human effort per accepted change and correct, timely workflow outcomes. Report observed effort, checks and gaps rather than extrapolating annual savings from a demo. The brief also limits the complete exercise to three-to-four hours and requires a video of at most five minutes plus a one-page decisions summary.

Devin should update this README after implementation with actual setup/run/reset commands, demo accounts, verification results, known gaps and the module extension path. Material choices belong in the decision log with real recorded timestamps; earlier chat times that were unavailable remain explicitly unknown. Normal coherent Git commits and pushes are authorized; preserve unrelated local changes. [Git history](https://github.com/samuel-zhang01/Cognition-Take-Home-Assessment/commits/main) records publication batches.
