from app.core.security import UserRole, has_permission
from app.core.logging import get_logger

logger = get_logger(__name__)


class GovernanceService:
    """
    Applies enterprise AI governance rules before and after generation.
    - Role-based access control on data scope
    - Grounding status assessment
    - Disclaimer injection for ungrounded answers
    """

    def check_access(self, role: UserRole, permission: str) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        allowed = has_permission(role, permission)
        if not allowed:
            logger.warning("Access denied | role=%s | permission=%s", role, permission)
            return False, f"Role '{role}' does not have '{permission}' access."
        return True, ""

    def assess_grounding(
        self, sources_count: int, tools_called_count: int
    ) -> str:
        """Determines grounding status from evidence available."""
        if sources_count > 0 and tools_called_count > 0:
            return "grounded"
        if sources_count > 0 or tools_called_count > 0:
            return "partially_grounded"
        return "not_grounded"

    def apply_disclaimer(self, answer: str, grounding_status: str) -> str:
        """Appends a disclaimer when the answer is not grounded in retrieved evidence."""
        if grounding_status == "not_grounded":
            return (
                answer
                + "\n\n---\n"
                + "_Disclaimer: This answer is based on the model's general knowledge "
                "and is not grounded in retrieved documents or structured data. "
                "Verify before taking action._"
            )
        return answer
