from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    key: str
    title: str
    path: str
    description: str
    owner: str
    replaces: str
    controls: tuple[str, ...]
    source_files: tuple[str, ...]


@dataclass(frozen=True)
class NavItem:
    key: str
    title: str
    path: str


MODULES = (
    ModuleSpec(
        key="counterparties",
        title="Counterparty reviews",
        path="/counterparties",
        description="Review financial-strength and payout evidence for onboarding decisions.",
        owner="Rita Patel",
        replaces="Power Apps KYC review queue",
        controls=("permissions", "reason", "version check", "audit", "import", "export"),
        source_files=(
            "app/modules/counterparties.py",
            "app/templates/counterparties.html",
            "app/templates/counterparty_detail.html",
        ),
    ),
    ModuleSpec(
        key="claims",
        title="Claims & refunds",
        path="/claims",
        description="Review customer claims and record an approve or reject decision.",
        owner="Colin Murray",
        replaces="Power Apps refunds dashboard",
        controls=("permissions", "reason", "version check", "audit", "import", "export"),
        source_files=(
            "app/modules/claims.py",
            "app/templates/claims.html",
            "app/templates/claim_detail.html",
        ),
    ),
    ModuleSpec(
        key="flags",
        title="Feature flags",
        path="/flags",
        description="Review environment-level flags with owner and change history.",
        owner="Fiona Grant",
        replaces="Power Apps feature-flag admin",
        controls=("permissions", "reason", "version check", "audit", "export"),
        source_files=("app/modules/flags.py", "app/templates/flags.html"),
    ),
    ModuleSpec(
        key="access_reviews",
        title="Access reviews",
        path="/access-reviews",
        description="Review employee access to business systems for the current quarter.",
        owner="Nina Okafor",
        replaces="New: planned tool 4 of 10+",
        controls=("permissions", "reason", "version check", "audit", "import", "export"),
        source_files=(
            "app/modules/access_reviews.py",
            "app/templates/access_reviews.html",
            "app/templates/access_review_detail.html",
        ),
    ),
)

CORE_MODULES = tuple(module for module in MODULES if module.key != "access_reviews")
NEW_MODULES = tuple(module for module in MODULES if module.key == "access_reviews")

NAV_GROUPS = (
    (
        "Overview",
        (
            NavItem("dashboard", "Dashboard", "/"),
            NavItem("business-case", "Business case", "/business-case"),
            NavItem("security", "Security & controls", "/security"),
        ),
    ),
    (
        "Apps",
        tuple(
            NavItem(module.key, module.title, module.path)
            for module in CORE_MODULES
        ),
    ),
    (
        "New apps",
        tuple(
            NavItem(module.key, module.title, module.path)
            for module in NEW_MODULES
        )
        + (NavItem("add-app", "+ Add an app", "/apps#add"),),
    ),
    (
        "Records",
        (
            NavItem("data", "Import & export", "/data"),
            NavItem("audit", "Audit log", "/audit"),
        ),
    ),
)
