# Power Apps pricing evidence and customer economics

Researched 15 October 2026. US commercial USD list prices, generally annual billing, excluding tax and negotiated discounts. This is supporting research; no customer invoice or contract was supplied. Sixty engineers is not a licensed-user count. Numerical scenarios below are calculations, not claims about this customer.

## Findings that most affect the decision

1. Premium licenses the **user across unlimited apps**. Adding ten apps to the same licensed audience does not itself multiply the base license charge. Marginal integration, capacity, administration and maintenance costs still exist. The relevant licensing KPI is avoidable spend by distinct user and entitlement, not spend divided by three current apps. [Current US pricing](https://www.microsoft.com/en-us/power-platform/products/power-apps/pricing/)
2. The claimed future price increase is verified: Microsoft's 9 September 2026 announcement moves ordinary Premium from $20 to $22/user/month and the 2,000-seat-minimum offer from $12 to $14, effective 1 January 2027. Existing subscriptions retain their current price to term end; new purchases, renewals and co-terminations with terms beginning on/after that date receive the new list price. Only these Premium SKUs are affected by that announcement. [Official announcement](https://www.microsoft.com/en-us/licensing/news/power-apps-premium-price-update)
3. The $5 per-app plan is channel-dependent, not universally retired. The January notice, clarified in March, preserves existing Enterprise Agreement renewals, allows existing/new CSP purchases and renewals, and treats MPSA differently: use until agreement end, then a 60-day migration window. Obtain a quote in the customer's actual channel. [Revised notice](https://www.microsoft.com/en-us/licensing/news/power-app-per-app-end-of-sale), [March CSP clarification](https://microsoftpartners.powerappsportals.com/abs/Blog/?title=CSP+Per+App+EoS+Clarification)
4. The worst case has no defensible universal maximum without user, storage, activity and support assumptions. Model a bounded stress case. Present $250K as the stated bill to reconcile, not evidence that 60 users cost $250K in base licenses.

## Main-document-ready plan matrix

| Option | Charging unit / list rate on research date | Practical consequence for this customer |
|---|---|---|
| Developer Plan | Free for development/testing, not production | Useful for experiments; does not eliminate production-user entitlements. |
| Premium | $20/user/month, paid yearly; $22 under applicable terms from January 2027 | Unlimited apps per assigned user; best modeled using distinct user overlap across the whole portfolio. |
| Premium volume offer | $12/user/month with **2,000-seat minimum**; $14 from January 2027 | Minimum annual base bill is $288,000 now / $336,000 future. Cannot price 60 users at $12. |
| Per-app subscription | $5/user/app/month, subject to channel availability | Rights attach to an app within an environment; useful for narrow audiences. Do not multiply by app count before checking whether Premium is cheaper. |
| Per-app PAYG | $10/monthly active user/app | Meter actual monthly user–app pairs. One person using three apps is three pairs; usage frequency within the same month does not reduce that charge. |

Sources: [Current pricing and Developer Plan](https://www.microsoft.com/en-us/power-platform/products/power-apps/pricing/), [per-app definition and $5 rate](https://learn.microsoft.com/en-us/power-platform/admin/powerapps-flow-licensing-faq), [PAYG counting](https://learn.microsoft.com/en-us/power-platform/admin/pay-as-you-go-meters), [2027 prices](https://www.microsoft.com/en-us/licensing/news/power-apps-premium-price-update). The current pricing page omits the per-app subscription while the FAQ still describes it; the channel notice resolves its availability more precisely.

### Illustrative base-license arithmetic

Assume the stated number of users all need every listed app all year. PAYG columns additionally assume every user opens every app in every month. These are deliberately unoptimized comparisons; a sensible licensing mix would move heavy multi-app users to Premium. They exclude capacity, standalone automation, support and implementation.

| Scenario | 60 users | 250 users | 1,000 users |
|---|---:|---:|---:|
| Premium, $20 × users × 12; either 3 or 13 apps | $14,400 | $60,000 | $240,000 |
| Premium, future $22 × users × 12; either 3 or 13 apps | $15,840 | $66,000 | $264,000 |
| Per-app, $5 × users × 3 × 12 | $10,800 | $45,000 | $180,000 |
| Per-app, $5 × users × 13 × 12 | $46,800 | $195,000 | $780,000 |
| PAYG, $10 × users × 3 × 12 | $21,600 | $90,000 | $360,000 |
| PAYG, $10 × users × 13 × 12 | $93,600 | $390,000 | $1,560,000 |

Calculated break-even, before differing capacity/rights: at $20 Premium, four $5 app assignments tie and five favor Premium. At $22, four cost $20 and five cost $25, so five still favor Premium. PAYG ties current Premium at two active apps per month; three favor Premium. At $22, two PAYG app pairs cost $20 and three cost $30. Seasonal activity can change the annual comparison: $240 buys 24 PAYG user–app months; $264 buys 26.4. Apply the actual per-user monthly usage distribution and contract commitments.

Existing Premium users are excluded from the PAYG app meter; eligible Microsoft 365 users using only standard connectors can also be excluded. Conversely, enabling PAYG in an environment causes available per-app passes to be ignored there. Inspect entitlements before combining plans. [Meter rules](https://learn.microsoft.com/en-us/power-platform/admin/pay-as-you-go-meters)

## Adjacent charges and rights to inventory

**Automation.** Power Apps includes cloud automation within the app's context, including premium/custom connectivity in context; it is not an entitlement to arbitrary unrelated flows or RPA. Associate relevant automated/scheduled flows with the app. Desktop attended/unattended RPA needs appropriate additional rights. Removing the app can leave retained flows needing separate licenses. [Power Automate licensing FAQ](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/faqs)

| Standalone automation SKU | Current published annual-billing rate | Budgeting use |
|---|---:|---|
| Power Automate Premium | $15/user/month = $180/user/year | Relevant users and automation contexts; do not automatically add it for every Power Apps user. |
| Process | $150/bot/month = $1,800/year | Core process/unattended automation; license allocation and concurrency matter. |
| Hosted Process | $215/bot/month = $2,580/year | Includes a Microsoft-hosted machine. |
| Process Mining add-on | $5,000/tenant/month = $60,000/year | Separate optional scope; no evidence this client uses it. |

[Official Power Automate prices](https://www.microsoft.com/en-us/power-platform/products/power-automate/pricing)

**Dataverse.** Premium accrues 250 MB database and 2 GB file per user into tenant capacity, rather than an isolated quota per app. Per-app accrues 50 MB database and 400 MB file. Shared workloads consume the pool. License removal can remove earned capacity, so a retained archive or another Power Platform application can strand storage charges. [Capacity entitlement FAQ](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/faqs)

The October 2026 guide lists additional prepaid capacity at $40/database GB/month, $2/file GB/month and $10/log GB/month, billed annually; database Tier 2 is $30/GB/month with a 1,000-GB minimum. Its default Premium table says 20 GB database, but a later worked example still uses 10 GB: verify actual tenant entitlement rather than silently picking one. [October licensing guide, pp. 20–22](https://go.microsoft.com/fwlink/?linkid=2085130)

The capacity page describes eligible borrowing in one direction: unused database can cover log/file, unused log can cover file. File cannot cover a database deficit. Capacity optimization should use effective deficit after borrowing, growth and an operating buffer. [Storage enforcement and borrowing](https://learn.microsoft.com/en-us/power-platform/admin/capacity-storage)

PAYG storage rates differ: $48/database GB/month, $2.40/file GB/month and $12/log GB/month above applicable allocations; the meter page describes 1 GB database and 1 GB file free per PAYG environment and immediately metered logs. Confirm allocated capacity and actual Azure billing behavior. [PAYG storage meter](https://learn.microsoft.com/en-us/power-platform/admin/pay-as-you-go-meters)

**Requests.** Official daily entitlements include 40,000 requests for Premium and 6,000 for per-app/PAYG, with separate connector/service-protection constraints. Automated flow transition-period limits currently differ from official future per-user limits. Budget for actual activity, including retries/pagination; a nominal unlimited-app entitlement does not mean unlimited throughput. [Request limits, updated 14 October 2026](https://learn.microsoft.com/en-us/power-platform/admin/api-request-limits-allocations)

A Requests add-on is documented at $50/month for 50,000 additional daily requests, but cannot currently be assigned to users/flows during the transition. The older broad FAQ says 10,000 for the same price. Use the specific current add-on/limits documentation and confirm with Microsoft; for a throttled cloud flow it directs customers toward Process licensing. The request PAYG meter is explicitly not available/not billed today. [Specific add-on page](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/add-ons), [request meter status](https://learn.microsoft.com/en-us/power-platform/admin/pay-as-you-go-meters)

**External audiences.** A KYC portal for applicants is a different audience and product boundary from an internal reviewer queue. Power Pages lists $200/100 authenticated users/site/month or $75/500 anonymous users/site/month, paid yearly. Capacity and website overlap matter; do not casually assign applicant seats from the engineer count. Guest canvas users still need appropriate Power Apps licensing. No evidence says external applicants use these three internal apps. [Power Pages pricing](https://www.microsoft.com/en-us/power-platform/products/power-pages/pricing), [guest canvas licensing](https://learn.microsoft.com/en-us/power-platform/admin/powerapps-flow-licensing-faq)

**Managed Environments and code apps.** Managed Environment entitlement is included with qualifying licenses/meters; activating it requires qualifying active usage, not one admin license for the whole tenant. PAYG can qualify, but the app meter does not automatically license unrelated flows. [Managed Environment licensing](https://learn.microsoft.com/en-us/power-platform/admin/managed-environment-licensing)

Code apps currently support Premium, PAYG, App Pass or auto-claim (assigning an available Premium license). They offer custom React/Vue code with managed hosting, Entra and platform policies; this is a customization path, not a license-exit path. Current limitations include no Secure Implicit Connections and no Power Platform Git integration. Source Git and platform Git integration are distinct. [Code apps overview, updated 24 September 2026](https://learn.microsoft.com/en-us/power-apps/developer/code-apps/overview)

## Reconciling the stated $250K and deciding what can disappear

Calculated: $250,000 / ($20 × 12) = 1,041.7 full-price Premium user-years. That is a diagnostic equivalent, not an inferred seat count. If there were 60 actual full-price Premium users, base licensing would explain only $14,400, leaving $235,600 to identify. At 250 users it explains $60,000, leaving $190,000; at 1,000 it explains $240,000, leaving $10,000. The 2,000-seat volume minimum itself exceeds the stated bill at current list price, so a claimed volume offer would need a discount or broader agreement explanation.

Storage can be material: **100 GB of additional prepaid database capacity costs $48,000/year**, whereas 100 GB file costs $2,400/year and 100 GB log costs $12,000/year. Those are charged add-on units above usable entitlements, not total stored data. A database-heavy bill and a seat-heavy bill imply different optimization and exit plans. Moving three screens while retaining Dataverse does not establish avoidance of either charge.

For each invoice line classify: cancelable at next renewal; retain for another application; retain for archive/audit access; transitional dual-run cost; or unrelated bundled commitment. Record earliest savings date and contract owner. A migrated app only saves a Premium user license if that user no longer needs other covered apps and procurement can reduce the committed quantity. Ten new apps may increase the value of existing seats without increasing that line item.

Replacing the frontend while indirectly using Power Platform services/data is not automatically a license exit. Microsoft explicitly applies licensing to direct and indirect use and prohibits connection-pooling/multiplexing as a way to reduce required licenses. Review any proposal to retain Dataverse behind a custom API or service account. [Microsoft licensing and multiplexing guidance](https://www.microsoft.com/en-us/licensing/product-licensing/power-platform)

Recommended customer KPIs: annual **avoidable** vendor cash spend and its realization date; annual incremental engineering/platform ownership cost; unit cost per completed KYC review/refund/controlled flag change; human time per accepted change; and control/availability guardrails. The relevant decision compares a license-optimized retained platform with an equivalent operated replacement, after migration and archive costs. A per-screen cost comparison misses the customer's operating outcome.

## Evidence limits

No public list-price page establishes this company's contract, support bundle, user count, app overlap, data footprint, negotiated discount, renewal date or avoidable amount. The Microsoft guide is explanatory and says the agreement controls. Several official pages contain stale or inconsistent details: per-app availability, default capacity examples and request add-on size. Preserve these conflicts in the research and resolve them using customer billing/tenant reports plus a written channel quote; do not claim that online research alone makes the $250K savings certain.
