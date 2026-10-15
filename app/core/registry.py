from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    key: str
    title: str
    path: str
    description: str
    owner: str
    proxy_for: str


MODULES = (
    ModuleSpec(
        "counterparties",
        "Insurance counterparties",
        "/counterparties",
        "Review synthetic insurer and claims-provider evidence for a fintech KYC queue.",
        "Reviewer",
        "KYC review queue",
    ),
    ModuleSpec(
        "claims",
        "Claims",
        "/claims",
        "Inspect and simulate approval of synthetic claims in a refunds workflow.",
        "Claims operator",
        "Refunds dashboard",
    ),
    ModuleSpec(
        "flags",
        "Feature flags",
        "/flags",
        "Change demonstration feature flags with a reason and an audit trail.",
        "Flag operator",
        "Feature-flag admin",
    ),
    ModuleSpec(
        "audit",
        "Shared audit",
        "/audit",
        "Review the shared, role-scoped history of operational changes.",
        "Auditor",
        "Cross-tool audit (shared foundation)",
    ),
    ModuleSpec(
        "access_reviews",
        "Access reviews",
        "/access-reviews",
        "Review employee access to business systems for the current quarter.",
        "Access reviewer",
        "New: planned tool 4 of 10+",
    ),
)
