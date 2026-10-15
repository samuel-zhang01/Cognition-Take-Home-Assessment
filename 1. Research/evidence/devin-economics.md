# Devin: procurement, usage economics and development security

Checked against primary public sources on **15 October 2026**. Supporting research for `0.research.md`; this document makes no purchase, deploys nothing and assumes no access to the customer's actual agreement. Vendor statements establish documented behavior, not measured productivity or certification of the software Devin produces.

## What matters to this customer

For a US Series C fintech with about 60 engineers, the decision is whether the same dependable operational outcomes can be delivered with less total cash cost and scarce engineering capacity. An agent subscription is one component of the development cost. It does not supply the production application's complete identity, authorization, database, evidence retention, monitoring, recovery or support arrangement.

The number of engineers, the number of app builders and the number of people operating KYC/refunds/flag tools are separate populations. Do not buy or model 60 agent seats merely because the company employs 60 engineers. Start with the engineers accountable for the shared platform and representative changes; expansion needs evidence.

## Primary-source facts

### D1. Current public prices and entitlements

[Devin pricing](https://devin.ai/pricing)

| Plan | Public USD price | Relevant entitlement |
|---|---:|---|
| Free | $0 | Limited individual usage; no Cloud sessions in comparison table |
| Pro | $20/month | One member; Cloud access; up to 10 concurrent sessions |
| Max | $200/month | One member; higher quota; up to 10 concurrent sessions |
| Teams | See conflict below | Up to 200 users; collaboration, centralized billing and analytics; unlimited concurrent sessions |
| Enterprise | Custom | Unlimited members; SAML/OIDC SSO, enterprise controls, dedicated deployment option; unlimited concurrent sessions |

The comparison table places VPC deployment and teamspace isolation in Enterprise. Paid extra usage is described as charged at API pricing. No fixed numeric quota, all-in price per task or public Enterprise ACU rate is supplied here. Unlimited concurrency does not promise unlimited consumption. Annual price/commitment was not published in the reviewed pricing grid.

**Official inconsistency:** the Teams card literally says **“$80/month for team plan + $40/mo per full dev seat”**; D2 instead treats $80 as a minimum including seat charges. Obtain written confirmation or an actual checkout/order form. Do not silently resolve the conflict in a customer forecast.

### D2. Self-serve billing mechanics

[Self-serve plans](https://docs.devin.ai/admin/billing/self-serve)

Pro and Max are individual accounts that cannot be shared. Teams full seats cost $40/month and have Pro-equivalent quota plus Desktop. Flex seats have no recurring seat charge or included quota, consume shared credits and lack Desktop access. All members count toward 200.

The documented Teams minimum is $80/month: zero full seats buys $80 of credits; one buys a $40 seat plus $40 credits; two cost $80 without credits; three cost $120. Thus it contradicts a literal base-plus-seat reading of D1.

Pro/full seats have daily and weekly quotas; Max has only a larger weekly quota. Numeric allowances are not specified. Purchased credits carry forward without expiry; auto-reload and default session spend settings exist. Teams automations and Devin Review consume shared credits directly, outside full-seat quota. Legacy self-serve ACU balances migrated to equivalent-dollar credits; current Core/$500 Team pricing should not be used.

These mechanics do not establish an exact universal credit-to-dollar, token or task conversion. Use actual charged dollars and invoices, not an invented hourly agent rate.

### D3. Enterprise pricing and spend controls

[Enterprise billing](https://docs.devin.ai/admin/billing/enterprise)

Enterprise ACUs are priced in the customer's order form and are explicitly distinct from self-serve quota/credits. Billing timing also follows that form. Consumption is available at enterprise, organization, user and session levels. Organization caps cover Cloud, Review, Desktop, JetBrains and CLI consumption billed there. When an organization reaches its cap, new work is blocked; per-user policies also exist. The page does not establish that every in-flight job instantly stops exactly at the threshold. Confirm cap semantics and overrun behavior.

No public Enterprise rate, minimum spend, annual commitment, included professional services or VPC charge was verified. Each belongs in a quote, not an assumed unit economics model.

### D4. What accrues usage

[Usage](https://docs.devin.ai/admin/billing/usage)

Consumption depends on work performed: planning, context gathering, execution, browser/code actions and some VM/network cost. Complexity, repository/context size, files changed, runtime and repeated conversation affect consumption. Waiting for a response, tests or repository setup still has small VM overhead; sleeping has no usage. Default sleep follows 30 minutes of inactivity, with a configurable 5–120 minute range for Enterprise through its account team. Per-session usage is exposed through Session Insights; self-serve also shows quota and credit balances in Usage & limits.

An elapsed-hour forecast is therefore weaker than measured cost by task type, including failed attempts and retries.

### D5. A display conversion that must not become a price quote

[Session Insights](https://docs.devin.ai/product-guides/session-insights)

Insights is available for completed sessions without a separate analysis charge. The page describes usage, user messages, session size, issues and suggested improvements. For quota plans, the *session-size classification* converts overage cost to ACUs at $2 per ACU; Enterprise size thresholds scale by ten. This is not a published Enterprise rate or evidence that each billed ACU equals a fixed amount of human work or wall-clock time. Prefer invoices and the applicable plan's consumption reports for budgeting.

### D6. Development workflow

[When to Use Devin](https://docs.devin.ai/essential-guidelines/when-to-use-devin) and [SDLC integration](https://docs.devin.ai/essential-guidelines/sdlc-integration)

The documented environment includes shell, IDE, desktop and browser. Devin can run an app, inspect UI behavior, take screenshots and produce recordings. Documentation recommends explicit success criteria, repository context and bounded tasks. It supports parallel sessions, integrations, repeatable instructions and scheduled development work.

The SDLC page describes repository changes delivered as PRs under the customer's branch protections, with human engineers choosing whether to merge. It also describes test loops and first-pass review. Its vendor examples and speed/coverage claims are not forecasts for this fintech; neither a generated test suite nor a video establishes independently correct financial behavior.

### D7. Production hosting boundary

[Devin app deployments](https://docs.devin.ai/product-guides/deployment-capabilities)

Native deployment is an optional small-app/demo path, separate from normal customer CI/CD. It serves static frontends on public `devinapps.com` URLs and FastAPI backends via Fly.io. Enterprise organizations cannot use it; secure mode, enforced security profiles and network policies also prevent this path. Every native deployment requires explicit approval because it makes content publicly reachable. Existing applications generally ship through infrastructure, tooling and credentials the customer supplies.

A live prototype link does not establish private production access, a runtime SLA, data residency, backup, restore, audited change control or an operating team. Price those independently if an owned solution proceeds.

### D8. Vendor security, training and retention

[Security at Cognition](https://docs.devin.ai/admin/security)

Cognition states SOC 2 Type II certification since September 2024 and encryption in transit/at rest. It warns that output can contain bugs or insecure behavior and recommends review and branch protections. Repository access can be selected through the GitHub integration.

For paid self-serve accounts, model training is allowed by default until opt-out; Teams opt-out requires an administrator. Opt-out also enables zero retention at model providers. Enterprise training requires prior written consent. Provider zero retention is not zero retention by Cognition: the same page describes customer-relationship retention, with feedback/user-interaction retention as determined necessary by Cognition. Obtain the actual data settings and agreement before exposing internal material.

### D9. Public self-serve contract: sensitive-data and retention constraints

[Platform Terms of Service](https://cognition.com/legal/platform-terms-of-service)

Section 4.2 says customers agree not to process medical information or sensitive personal data including SSNs, birth dates, passport information, bank account and credit-card numbers using the Services. This is directly relevant to real KYC/payment records being exposed to a development agent. Section 3.3.3 preserves abuse, security, compliance and legal-process exceptions to ZDR. Section 3.1 assigns output rights to the customer, subject to applicable law; §2.5 provides no general availability guarantee. Subscription term/renewal follows the purchased subscription. Paid training opt-out and provider ZDR are also reflected in §3.3.1.

The appropriate research/prototype input is synthetic data. An owned app built from synthetic fixtures can later operate on production data within separately approved infrastructure; that does not mean production records need to enter Devin.

### D10. Enterprise contract is not automatic sensitive-data permission

[Master Services Agreement, updated 8 June 2026](https://cognition.com/legal/enterprise-terms-of-service)

Section 3.3 prohibits model training on Customer Data without express prior written consent. Section 4.3 also prohibits protected health information and listed sensitive personal data by default, but allows certain processing under a separate written agreement with safeguards. Enterprise alone therefore does not establish permission to submit KYC documents. Fees and term are set in the Order Form (§§5.1, 7.1); do not assume a universal annual term. Output evaluation remains the customer's responsibility (§2.4).

Section 2.3 also restricts public publication of benchmarks/performance information. If the actual evaluation uses Enterprise terms, have procurement confirm any permission needed for external publication of results. This research is not a legal interpretation of the customer's unknown signed contract.

### D11. DPA, subprocessors and security evidence

[Data Processing Agreement](https://cognition.com/legal/data-processing-statement) and [Trust Center](https://trust.cognition.ai/)

The DPA §11 directs subprocessors to delete data within 30 days of termination, with legally required retention exceptions. Appendix A describes agreement-term retention plus 30 days and says sensitive submissions are not intended. Appendix C lists infrastructure, logs/support and model subprocessors; locations include the US and an India support workflow. Thus a US-based company should still review the full processing chain and access locations rather than infer that every processor is US-only. Section 4 binds subprocessors to corresponding training restrictions.

The public Trust Center lists SOC 2 Type 2 and ISO/IEC 27001:2022, but reports/certificates require access and an NDA. This research did not inspect the audit scope, exceptions, report period, bridge letter or penetration-test findings. Obtain those before representing independent verification.

### D12. Controls to assess in a bounded development rollout

[Security profiles](https://docs.devin.ai/product-guides/security-profiles)

Profiles can limit network destinations, MCP servers, git write access, Devin management writes and the GitHub CLI token. Enterprise can enforce shared restrictions as a floor; recommended defaults can be overridden by appropriately permitted users. Profile updates take effect at boot/wake, not automatically in an already-running session. A network policy on Devin-managed VMs covers shell, browser and scripts. For customer-operated Outposts, the customer must enforce machine egress policy itself.

[OIDC workload authentication](https://docs.devin.ai/product-guides/oidc)

Devin supports short-lived session identity tokens for services such as AWS/GCP/Vault and customer APIs. The customer's trust policy determines the temporary scope. Session, organization and requesting-user claims support attribution in cloud-side audit logs. This reduces dependence on permanent keys; it does not by itself restrict business authority correctly. Test the issued permissions.

[Outposts](https://docs.devin.ai/cloud/outposts/overview)

Outposts moves command execution, files and repository operations to customer-operated machines, while inference and planning remain in Devin's cloud. Do not describe self-hosted workers as fully offline or as proof no code/context leaves the network. Add worker isolation, patches, egress enforcement, provisioning and monitoring to ownership costs if selected.

## Budgeting without fabricated task performance

The following is **proposed analysis**, not quoted pricing or predicted consumption.

1. Use the assessment's already-provided Devin access if available and record actual usage. A tool already made available has no new subscription purchase requirement for the assessment. Impute the appropriate commercial usage cost separately for a customer comparison.
2. For a later shared customer pilot, use two accountable builders, synthetic fixtures and one workflow plus a small reuse change. Pro/Max cannot be shared. Self-serve only makes sense if its actual identity, data and security terms meet the pilot's needs; otherwise request an Enterprise pilot quote first.
3. Hold two billing interpretations until resolved: D2 implies $80/month for two full seats; the literal D1 card implies $160/month. A **management-selected $200 extra-credit ceiling** would make a one-month agent-cash envelope **$280 or $360**, excluding tax, runtime services and labor. This is a budget cap, not an assertion the work will fit. Use session limits, monitor live, and check whether limits include ongoing work. If settings cannot enforce the desired ceiling, use manual stops and a smaller credit purchase.
4. Price human work explicitly. At an assumed $250,000 loaded annual cost divided by 2,000 paid hours, 40 pilot human hours cost $5,000 of allocated capacity. That is roughly an order of magnitude more than the illustrative agent allowance. It is an accounting assumption, not evidence of necessary effort or cash savings.
5. Do not automatically assign subscriptions to operators who merely use the finished internal apps. For a steady-state example, five builders imply $200/month under D2 or $280/month under the literal D1 reading, before extra usage. For reference only, 60 full builders would imply $28,800 or $29,760 per year before consumption. Neither is a requirement or an Enterprise quote.
6. Build ongoing consumption from observed monthly change demand. Record task family, attempts, all sessions, cost/credits/ACUs, human setup/review/remediation, final acceptance, defects and operating outcome. Failed tasks remain in the numerator. Treat automation and Review as separate workloads, especially on Teams where they bypass full-seat quota.

For each representative task family `k`, estimate:

`Monthly agent forecast = fixed plan cost + sum(expected attempts_k × measured incremental dollars per attempt_k) + automation/review dollars`

If starting from accepted task demand, use an observed acceptance rate to estimate attempts and retain tail/failed work in the sample. With a tiny pilot, report raw observations and ranges; a percentile from two tasks is not a reliable upper bound. Included quota makes marginal cash non-linear, so reconcile the forecast against actual plan quota, credit purchases and invoice cash. Credit purchases and consumption also differ in time because credits can carry forward.

For Enterprise, replace the self-serve formula with the quoted minimum/commitment plus metered ACUs and any separately priced services. Ask whether usage across Cloud, Desktop, CLI and Review shares the same pool and conversion. Never apply self-serve $2 display conversions or legacy $2.25 Core rates to that agreement.

## Customer KPIs and evidence needed

Proposed primary development metric:

`Accepted, operated changes per active human hour = changes meeting predeclared acceptance + quality requirements / total human setup + prompting + review + correction + deployment + follow-up time`

Do not equate a PR merge with value delivered. Pair it with elapsed lead time, escaped defects, rollback/rework, and operational owner acceptance. Avoid using many trivial PRs to inflate throughput; compare like-sized, pre-scoped task families. Include comparable human-only or current-platform changes where feasible, without extrapolating from a single task.

Business metrics sit above the agent metric:

| Workflow | Outcome to preserve/improve | Guardrail |
|---|---|---|
| KYC | Median and p95 time from complete case to authorized decision; aged backlog | Decision rework, unauthorized transitions, missing evidence |
| Refunds | Request-to-approved/submitted/successful refund by workflow stage | Duplicate/over-limit actions; unreconciled or failed refunds |
| Flags | Authorized request-to-observed production change | Wrong environment/targeting; stale propagation; emergency recovery |
| Portfolio | Actual annual spend avoided; total ownership cost; funded roadmap capacity | Availability/recovery, access control, audit completeness, maintenance backlog |

Thresholds must come from the customer's baseline and risk appetite. No public documentation establishes the current values, a Devin improvement percentage, or acceptable fintech error rates.

## Procurement questions with direct economic consequences

- Which written Teams billing interpretation applies, and what will the pilot's exact checkout/invoice contain?
- What are numeric quotas, reset times, model weights and all incremental tariffs? Are there model, tool, VM, storage, networking or external-provider charges beyond the displayed API-based price?
- What spend caps can be enforced per session, user, organization and automation? Can active sessions overrun them? Who can enable auto-reload or launch child sessions?
- What is the Enterprise minimum, term, renewal/escalator, unused-commitment treatment, overage rate, included support and dedicated/VPC/Outposts cost?
- Are SSO, provisioning/deprovisioning, teamspaces, role controls, enforced profiles, usage export and required audit events available in the purchased tier?
- Can all approved development data be processed under the contract? If sensitive data is genuinely needed, is there a separate written authorization and approved safeguard arrangement?
- Is training disabled for every surface/organization? Which vendors receive code/context, under which retention rules, and which support staff can access it? How are session history, indexes, recordings, feedback, logs and backups deleted/exported?
- What are the latest SOC/ISO scope and exceptions, incident notice terms, subprocessor change rules, and support/recovery commitments? Do these fit development needs without being mistaken for the runtime apps' commitments?
- Can source, build artifacts, tests and operational documentation be retained and operated without an ongoing Devin dependency? What software-licensing, warranty and IP review is still required?

## Changes recommended to the draft

The existing broad separation of development agent and production platform is supported. Enrich it with current prices, the official Teams conflict, builder/operator separation, the sensitive-data contractual restriction, provider-versus-Cognition retention, actual consumption measurement and an explicit no-public-Enterprise-rate statement. Keep all annual savings contingent on Power Apps spend being genuinely avoidable and on incremental ownership staying below it. Do not claim “all correct”: product pages conflict, signed terms are unavailable, numeric quotas are unpublished, and no client productivity/maintenance experiment has been run.
