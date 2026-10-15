ROLE_PERMISSIONS = {
    "reviewer": {
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
        "counterparty.review",
    },
    "claims_operator": {
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
        "claim.approve",
    },
    "flag_operator": {
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
        "flag.change",
    },
    "auditor": {
        "counterparty.read",
        "claim.read",
        "flag.read",
        "audit.read",
    },
}

AUDIT_SCOPE = {
    "reviewer": {"counterparties"},
    "claims_operator": {"claims"},
    "flag_operator": {"flags"},
    "auditor": {"counterparties", "claims", "flags"},
}
