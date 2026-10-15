ROLE_PERMISSIONS = {
    "reviewer": {
        "modules.read",
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
        "counterparty.review",
    },
    "claims_operator": {
        "modules.read",
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
        "claim.approve",
    },
    "flag_operator": {
        "modules.read",
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
        "flag.change",
    },
    "auditor": {
        "modules.read",
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
    },
    "access_reviewer": {
        "modules.read",
        "access_reviews.decide",
        "access_reviews.import",
    },
}

AUDIT_SCOPE = {
    "reviewer": {"counterparties"},
    "claims_operator": {"claims"},
    "flag_operator": {"flags"},
    "auditor": {"counterparties", "claims", "flags"},
    "access_reviewer": {"access_reviews"},
}
