import pytest
from app.core.security import UserRole
from app.services.governance_service import GovernanceService


@pytest.fixture
def svc():
    return GovernanceService()


def test_analyst_can_query_policy(svc):
    allowed, _ = svc.check_access(UserRole.ANALYST, "policy_query")
    assert allowed


def test_analyst_cannot_access_confidential(svc):
    allowed, reason = svc.check_access(UserRole.ANALYST, "supplier_confidential")
    assert not allowed
    assert "analyst" in reason.lower()


def test_admin_can_access_everything(svc):
    for perm in ["policy_query", "supplier_risk", "supplier_confidential", "po_analytics"]:
        allowed, _ = svc.check_access(UserRole.ADMIN, perm)
        assert allowed, f"Admin should have {perm}"


def test_grounding_status_grounded(svc):
    assert svc.assess_grounding(sources_count=3, tools_called_count=2) == "grounded"


def test_grounding_status_partial(svc):
    assert svc.assess_grounding(sources_count=2, tools_called_count=0) == "partially_grounded"
    assert svc.assess_grounding(sources_count=0, tools_called_count=1) == "partially_grounded"


def test_grounding_status_not_grounded(svc):
    assert svc.assess_grounding(sources_count=0, tools_called_count=0) == "not_grounded"


def test_disclaimer_added_when_not_grounded(svc):
    answer = svc.apply_disclaimer("Some answer.", "not_grounded")
    assert "Disclaimer" in answer


def test_no_disclaimer_when_grounded(svc):
    answer = svc.apply_disclaimer("Some answer.", "grounded")
    assert "Disclaimer" not in answer
