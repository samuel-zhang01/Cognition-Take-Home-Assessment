# KYC review features for the prototype

15 October 2026. Product-design research for the internal operations portal. These provider examples inform a proposed synthetic workflow; they do not identify the customer's provider or establish its KYC obligations.

## Useful provider patterns

| Primary source | What it establishes | Design implication |
| --- | --- | --- |
| [Stripe verification sessions](https://docs.stripe.com/identity/verification-sessions) | A verification session has an identity, reports and outcomes such as `verified` or `requires_input`, with failure details. | Link a case to a provider reference and show the result and reason. Preserve the difference between a provider check and the company's review decision. |
| [Stripe access to verification results](https://docs.stripe.com/identity/access-verification-results) | Sensitive results have separate access requirements. Stripe recommends considering its controlled-access dashboard and minimizing copied sensitive material. | Use synthetic summaries in this demo. A future integration can link to protected evidence rather than duplicating documents everywhere. |
| [Sumsub manual approval and rejection](https://docs.sumsub.com/docs/approve-and-decline-applicants-manually) | Reviewers inspect results; rejection/resubmission reasons and status-specific restrictions affect available actions. | Show why a case needs attention, require a decision reason and validate actions on the server. Do not offer every action in every state. |
| [Entrust Workflow Studio manual decisions](https://documentation.identity.entrust.com/getting-started/onfido-studio-product/) | Manual decisions can be part of a provider workflow. Entrust distinguishes those decisions from ongoing applicant-status management and describes a case-management boundary. | Treat the internal app as a review/coordination interface over provider outcomes rather than an identity-verification engine. |

## Proposed minimum KYC slice

1. **Review queue:** customer reference, review status, review-needed reason, case age and optional assigned reviewer. Search and filter on the server. Show unfinished work as well as completed cases.
2. **Case summary:** verification-provider reference, check summaries, relevant evidence summary and the current internal decision. Use synthetic fixtures with a small number of meaningful exception cases.
3. **Controlled next action:** approve, reject, or request information if that action is selected for scope. Require a reason; enforce role, valid transition and expected version at the server. The client's policy would determine which checks allow approval.
4. **History:** actor, action, reason, time, previous/new state and version, visible to an appropriately scoped auditor. Commit accepted state and its history together.
5. **Work visibility:** pending/needs-information state and case age. An approval rate alone is not the customer outcome; legitimate completion and decision quality matter.

These are proposed application requirements, not a claim that all providers use the same states or that an internal approval overrides a provider check. Actual email/SMS requests to applicants, OCR, face matching, sanctions engines, real document uploads, two-reviewer approval and a configurable workflow editor would each add scope. A simulated request-information action would record internal state/history only unless a communication integration is explicitly built and demonstrated.

## Demonstration cases

- A case with sufficient synthetic evidence receives one authorized decision and a traceable reason.
- An incomplete case shows a clear next action instead of silently disappearing from the queue.
- An auditor can inspect permitted history but cannot submit a review decision through the API.
- A stale second review is rejected without overwriting the first accepted decision.

Keep provider integration behind a narrow adapter boundary. A fixture adapter demonstrates the code boundary and data contract; it does not establish compatibility with an actual provider. Test real credentials, permissions, errors and webhook behavior separately if real integration is later chosen.

## Data architecture and MCP

The official [MCP architecture](https://modelcontextprotocol.io/docs/learn/architecture) describes AI hosts and clients connecting to servers that expose capabilities such as tools and resources. MCP can expose an application API to an AI client; it is not itself an application database or a replacement for business authorization.

For this prototype, the proposed path is browser → shared server API → relational data store and provider adapters. It fits related records, explicit permissions and transactional state/history writes. A single demo database does not prove that three unrelated production systems have been integrated. Demonstrate shared identifiers, consistent permissions and actual reuse, then record the external integration gaps. Add MCP only if a specific AI-to-application interaction is part of the agreed demo.
