# Insurance proxy and Power Apps code app comparison

15 October 2026. Samuel selected insurance-informed examples because of his own experience and interview input. The assessment's customer remains a fintech; the proxy makes workflow decisions concrete without claiming discovery of that customer's actual product or policies.

## Map the proxy to the assessment

| Fintech brief | Insurance-informed demonstration | Capability being tested |
| --- | --- | --- |
| KYC review queue | Insurer/counterparty review with financial-strength evidence and a recorded human decision. | Review queue, evidence provenance, scoped decisions, reasons and history. |
| Refunds dashboard | Claim/payment request tracking and, if selected, a simulated approval. | Related records, financial-operation permissions, state validation and reconciliation visibility. |
| Feature-flag administration | Sandbox workflow configuration with controlled changes. | Shared authorization, version checks, change reasons and audit events. |

Insurer financial-strength review is counterparty due diligence; it does not demonstrate a complete identity-verification/KYC system. A claim/payment request also has different rules from a merchant refund. Keep these mappings explicit in the README and presentation, then describe what fintech discovery would change.

Suggested introduction: “I used insurance workflows I understand to make the proof of concept concrete. The transferable evidence is the shared integration, permission, audit and maintenance pattern. For this fintech, I would validate the actual KYC, refund and flag requirements with its operators before production design.”

## Rating evidence and synthetic data

[AM Best](https://web.ambest.com/ratings-services/rating-service-definitions) distinguishes financial-strength, issuer-credit and other rating types. Its ratings are opinions rather than guarantees. [S&P Global](https://www.spglobal.com/ratings/en/products/financial-strength-rating) describes insurer financial-strength ratings as opinions on the ability to pay policies and contracts. A financial-strength rating is not an observed payout-speed metric or a prediction that a particular claim will be paid.

[Lloyd's](https://www.lloyds.com/about-lloyds/investor-relations/ratings) publishes externally assigned ratings of the market and explains the common security supporting its syndicates. Preserve the distinction between a market rating, an individual legal entity's rating and any separately defined syndicate/oversight assessment.

For the prototype, propose fictional counterparties and clearly synthetic evidence. Store rating agency/source, rating type, rated entity, entity/market scope, value, as-of date and evidence reference separately. Do not invent current ratings for real insurers or treat different agency scales as one arithmetic score. Any payout history should be a separate synthetic dataset with its own definition and dates. Real feeds, reuse rights, matching, freshness and source conflicts require a later integration decision.

## Two contribution paths

Samuel confirmed that engineers should add modules using Devin, and that non-engineers should be able to initiate changes with Devin that then receive engineering code review.

The proposed proof is a bounded change request or module template, a Devin-generated patch, checks and engineer review before release. This preserves a familiar review path while testing whether business users can express useful changes. It does not require constructing a second in-app AI platform or a drag-and-drop builder. Business application permissions and repository merge/release permissions are separate controls.

## Why code apps deserve a bounded comparison

Microsoft documents custom frontends, Entra integration, connectors, managed policies and continued end-user licensing for code apps. This can support a third path: custom code authored with Devin while retaining selected Power Platform capabilities. [Overview](https://learn.microsoft.com/en-us/power-apps/developer/code-apps/overview)

The runtime hosts HTML/JavaScript/TypeScript single-page applications. It does not host an arbitrary generated application server; connector and backend authorization must be evaluated for the chosen data path. [Architecture](https://learn.microsoft.com/en-us/power-apps/developer/code-apps/architecture)

Code apps can participate in solutions and pipelines; ordinary source Git is distinct from Power Platform's source integration. [ALM](https://learn.microsoft.com/en-us/power-apps/developer/code-apps/how-to/alm)

### Documentation comparison and later optional check

Samuel subsequently reiterated that the demo must remain simple and buildable within two hours. For this run, retain a documentation-backed code-app comparison. The steps below describe a possible later, separately scoped feasibility check; they are not a second prototype commitment. The decision log preserves the earlier ten-minute spike proposal and its replacement by the simpler scope.

1. Check environment access, code-app enablement and applicable licensing.
2. Test one small read-only counterparty/rating view through one supported data path. Record whether the connection is a fixture, real connector or API; do not equate them.
3. Identify what the host supplies and where record/action authorization, application-server logic and audit persistence remain owned.
4. Record actual setup/publish friction if exercised. Publishing into a Microsoft tenant requires an identified intended development destination; do not change tenant policy or purchase services to unblock a spike.
5. Compare retained license cost plus any custom backend cost with the owned-portal path. Customization value can justify the hybrid even when it removes no Microsoft licenses.

The main two-hour experiment remains the shared portal. A second full implementation would displace the shared-control, maintenance and review evidence the customer cares about. Label code-app findings as documented, demonstrated or untested according to what was actually checked.
