# Interview evidence: capacity, customization and ownership

Added 15 October 2026. Source: interview excerpt supplied by Samuel in this conversation. Interview date, participant identity/role, speaker labels, recruitment method and relationship to the prospective client were not supplied. This is qualitative practitioner input; it does not establish the hypothetical client's staffing, contract, outcomes or vendor offer. Do not infer an interview sample size from one supplied excerpt.

**Terminology correction confirmed by Samuel:** references transcribed as “Cognizant” mean **Cognition/Devin**. Retain the distinction between Devin agent usage and any separately agreed human engineering, deployment or enablement engagement. The correction does not establish that a particular service is included in a subscription.

## What the excerpt actually contributes

Short quotations below preserve interview wording. Without speaker labels they are attributed to the excerpt, not to an identified participant. Interpretations and proposed tests are separate columns.

| Interview evidence | Interpretation for this decision | Evidence still needed |
| --- | --- | --- |
| Five categories are proposed: cost, customization, skills, maintainability and external help. The speaker corrects “customer” to customization. | Use these as five decision lenses. Customer operational outcomes and control requirements still apply across all five. | Customer priorities and current workflow outcomes; no interview-derived ranking or weighting is established. |
| The stated ongoing cost is a quarter of a million per year; Microsoft licenses are described as yearly rolling. | Investigate annual renewal as a possible exit point and model the actual savings date. | Signed term, notice deadline, SKU quantities, minimum commitments and residual spend. Annual renewal does not establish mid-term cancellation or refunds. |
| “three years run away” | The wording may refer to runway or a planning horizon. Retain the existing three-year comparison as an analytical horizon. | Actual cash runway, decision horizon and liquidity constraints. Do not report three years of runway as a customer fact. |
| Customization, creation, ongoing maintenance and training are emphasized. | Evaluate useful changes to real workflows, including who can make them after the original builders leave. | Representative backlog, current workarounds, operator validation and training/change effort. A bespoke interface is not automatically useful customization. |
| “sixty engineers” is contrasted with “sixty brokers.” | Technical capability affects the choice, but headcount and job titles are weak proxies for relevant skills. | Named people with the required application, identity, integration, domain and operating skills. Do not infer that all 60 can maintain fintech internal tooling. |
| The engineers “might already be at capacity doing other work.” | **Capability and availability are separate.** Devin may add execution capacity while review and domain decisions remain constrained. | Available engineering hours, review queues, competing roadmap commitments and a funded recurring owner. This is a possible constraint, not a verified utilization finding. |
| External help is described as “on-demand capacity” that can build and then leave, avoiding additional full-time hiring. | A timeboxed Cognition-assisted engagement followed by internal ownership is a candidate delivery model if commercially available. | Actual services scope, availability, fees, client time, handover and support terms. Avoiding a new hire does not eliminate the cost of existing staff time. |
| External engineers could be “up and running within a couple of days.” | Faster access to delivery capacity is a hypothesis to test. | Separate time to secure access, first reviewed change and first operationally accepted release. No two-day staffing, delivery or production-readiness promise is established. |
| “one and done” and later having to call people back both appear. | The interview itself surfaces the tension between project delivery and continuing ownership. | Independent maintenance exercise, defect support, escalation, documentation, retraining and the cost of renewed vendor help. |
| Vendor stability and “all eggs in one basket” are raised. | Consider business continuity, commercial dependence, data portability and dependence on individual maintainers. | Dependency map, export/recovery tests, contract exit terms and owner continuity. No vendor financial-stability assessment was supplied. |

The closing recommendation is unclear in the transcript. It does not support attributing a final “build internally” or “stay on Microsoft” verdict to the interviewee. Conversational agreement and leading questions are not a validated recommendation. Off-topic jokes and closing banter do not contribute decision evidence.

## What the clarification means for delivery options

Three decisions should be made separately:

1. **Platform/runtime:** retain Power Apps, use Power Apps code apps, or operate owned applications on selected infrastructure.
2. **Initial delivery:** internal makers/engineers using Devin, or a separately scoped Cognition-assisted engagement if offered for this client.
3. **Continuing ownership:** an internal team with funded capacity, a separately contracted support service if available, or a defined combination.

Devin is an execution tool within those arrangements. Purchasing usage does not itself appoint an accountable application maintainer or buy a human project team. Help setting up Devin also differs from a commitment to deliver, migrate and support thirteen business applications.

Primary-source check: Cognition's January 2026 deployment example describes forward-deployed AI engineers supporting project selection, engineer enablement and ROI measurement. It concerns a specific partnership; it does not establish a four-person team, public day rate, immediate availability, finished-app delivery or maintenance entitlement for this Series C fintech. [Cognition deployment example](https://cognition.com/blog/cognizant-cognition). The partner named in that article is an external example, not a reversal of Samuel's terminology clarification.

The commercial scope for this customer must be confirmed in a proposal/order form. Compare agent usage, human enablement, application delivery and continuing support as separate cost items. The existing research's current plan and terms evidence remains the source for subscription mechanics.

## How the interview changes the economics

Retain the existing model: `net benefit = sum(avoidable spend - incremental operating cost) - transition cost`. Apply it to each delivery model rather than changing the equation.

- **Transition cost B:** internal specification/review, any external delivery/enablement fee, initial training, migration, handover and dual-running costs not recorded elsewhere.
- **Recurring cost R:** actual application maintenance, security/recovery work, operator support, refresher training, Devin consumption and any support retainer. Deduct incumbent work genuinely displaced.
- **Savings S:** charges that actually disappear at their contractual dates. A technically complete build does not cancel a Microsoft commitment.

Track transition cash separately from capacity consumed by already employed engineers. A timeboxed external fee can avoid permanent hiring, but still needs cash and internal coordination. Compare three-year cost and the maximum transition cash requirement; a favorable three-year total can coexist with an unaffordable first-year cash outflow. Budget approval and accounting treatment belong with Finance; the excerpt does not establish them.

Do not calculate regained capacity as agent runtime or the number of sessions. A useful proposed measure is `comparable baseline human hours - actual internal specification, prompting, review, correction, release and follow-up hours`. Include failed attempts and normalize for task scope. If earlier delivery creates business value, measure the actual workflow improvement; do not assign unmeasured revenue to speed.

## Proposed evidence before accepting internal ownership

These are acceptance proposals, not product capabilities already demonstrated or legal requirements.

| Test | Observable result | Cost/KPI implication |
| --- | --- | --- |
| Independent routine change | A designated maintainer who did not create the module makes a representative change from the repository and docs, passes checks and obtains operator acceptance. Record requests for builder help. | Tests useful customization, skill transfer and human effort per accepted change. |
| Deployment and recovery | The owning team can deploy and rehearse rollback/restore using client-controlled accounts and documented procedures in an approved test environment. | Tests continuing operational ownership and recovery objectives. |
| Access withdrawal | Temporary vendor/development credentials can be revoked while runtime operation and client release access remain available. | Tests dependency boundaries; development-agent access must not be a hidden runtime requirement. |
| Owner continuity | A primary and backup maintainer have explicit capacity, escalation responsibilities and access. | Tests staff dependence without pretending two full-time hires are necessarily needed. |
| Training and support accounting | Record initial instruction, refresher time, support interventions, unresolved gaps and the cost of re-engaging outside help. | Makes B and R realistic and identifies whether dependence is reducing. |
| Scope-change test | Operations supplies a meaningful KYC/refund/flag change with acceptance criteria. | Establishes that the result fits the business rather than merely offering generic screens. |

Report maintenance coverage as `tools with an accepted owner, access, runbook and demonstrated maintenance capability / tools proposed for production`, with exceptions named. Use it as an ownership gate, not a substitute for workload/reliability outcomes. Keep measured onboarding and dependency diagnostics underneath the existing three primary KPIs rather than creating a large new scorecard.

## Follow-up questions for the actual customer and Cognition

- Which people have both relevant skills and funded availability now? Which roadmap work would be delayed by internal delivery or review?
- Which changes must operators make without engineers, and what training would custom code add or remove?
- Is help needed to configure/adopt Devin, to deliver these applications, or to operate them? Who accepts each deliverable?
- What human assistance is actually available to this customer, when, at what fee and for how long? Is it included or separately contracted?
- What happens when the original builders leave or the named internal maintainer is unavailable? Which support and defect obligations continue?
- Which Microsoft charges can actually stop at the next annual renewal, and can the replacement and handover finish before the decision deadline?
- What cash can be committed during the overlap period, and how much recurring internal maintenance capacity is approved?

The interview strengthens the case for testing capacity relief and knowledge transfer. It does not settle build versus buy, prove spare capacity, establish savings or make maintenance a one-time activity.
