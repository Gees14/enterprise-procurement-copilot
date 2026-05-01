from enum import Enum


class UserRole(str, Enum):
    ANALYST = "analyst"
    MANAGER = "manager"
    ADMIN = "admin"


# Role permission hierarchy
ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.ANALYST: {
        "policy_query",
        "supplier_general",
        "po_summary",
        "item_classify",
    },
    UserRole.MANAGER: {
        "policy_query",
        "supplier_general",
        "supplier_risk",
        "po_summary",
        "po_analytics",
        "item_classify",
        "email_draft",
    },
    UserRole.ADMIN: {
        "policy_query",
        "supplier_general",
        "supplier_risk",
        "supplier_confidential",
        "po_summary",
        "po_analytics",
        "po_confidential",
        "item_classify",
        "email_draft",
        "system_config",
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def get_role_permissions(role: UserRole) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())
