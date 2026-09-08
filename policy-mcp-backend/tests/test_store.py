"""
Unit tests for the insurance policy store
"""

import sys
from pathlib import Path

import pytest

# Add src directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from store import PolicyStore
from types_import import CreatePolicyInput, SubmitClaimInput


class TestPolicyStore:
    """Test suite for PolicyStore"""

    @pytest.fixture
    def store(self) -> PolicyStore:
        """Create a fresh store for each test"""
        return PolicyStore()

    def test_create_policy(self, store: PolicyStore) -> None:
        """Test creating a new policy"""
        input_data = CreatePolicyInput(
            customer_id="CUST-TEST-001",
            policy_type="auto",
            start_date="2025-01-01",
            end_date="2026-01-01",
            premium=1500,
            coverage_options=["cov-001"],
            deductible=500,
            policy_limit=100000,
        )

        policy = store.create_policy(input_data)
        assert policy.customer_id == "CUST-TEST-001"
        assert policy.policy_type == "auto"
        assert policy.status == "active"

    def test_get_policy(self, store: PolicyStore) -> None:
        """Test retrieving a policy"""
        policy = store.get_policy("POL-1000")
        assert policy is not None
        assert policy.id == "POL-1000"

    def test_get_policy_not_found(self, store: PolicyStore) -> None:
        """Test retrieving a non-existent policy"""
        policy = store.get_policy("POL-9999")
        assert policy is None

    def test_list_policies(self, store: PolicyStore) -> None:
        """Test listing all policies"""
        policies = store.list_policies()
        assert len(policies) > 0

    def test_list_policies_by_customer(self, store: PolicyStore) -> None:
        """Test listing policies filtered by customer"""
        policies = store.list_policies("CUST-001")
        assert len(policies) > 0
        assert all(p.customer_id == "CUST-001" for p in policies)

    def test_get_coverage_options(self, store: PolicyStore) -> None:
        """Test retrieving all coverage options"""
        options = store.list_coverage_options()
        assert len(options) > 0

    def test_get_coverage_options_by_type(self, store: PolicyStore) -> None:
        """Test retrieving coverage options filtered by type"""
        options = store.list_coverage_options("auto")
        assert len(options) > 0
        assert all("auto" in o.policy_types for o in options)

    def test_submit_claim(self, store: PolicyStore) -> None:
        """Test submitting a claim"""
        input_data = SubmitClaimInput(
            policy_id="POL-1000",
            claim_type="collision",
            amount=3000,
            description="Test claim",
        )

        claim = store.submit_claim(input_data)
        assert claim.policy_id == "POL-1000"
        assert claim.status == "submitted"
        assert claim.id.startswith("CLM-")

    def test_list_claims(self, store: PolicyStore) -> None:
        """Test listing all claims"""
        claims = store.list_claims()
        assert len(claims) > 0

    def test_list_claims_by_policy(self, store: PolicyStore) -> None:
        """Test listing claims filtered by policy"""
        claims = store.list_claims("POL-1000")
        assert len(claims) > 0
        assert all(c.policy_id == "POL-1000" for c in claims)

    def test_create_multiple_policies(self, store: PolicyStore) -> None:
        """Test creating multiple policies generates unique IDs"""
        input1 = CreatePolicyInput(
            customer_id="CUST-A",
            policy_type="auto",
            start_date="2025-01-01",
            end_date="2026-01-01",
            premium=1000,
            coverage_options=[],
            deductible=500,
            policy_limit=100000,
        )

        input2 = CreatePolicyInput(
            customer_id="CUST-B",
            policy_type="home",
            start_date="2025-02-01",
            end_date="2026-02-01",
            premium=2000,
            coverage_options=[],
            deductible=1000,
            policy_limit=500000,
        )

        policy1 = store.create_policy(input1)
        policy2 = store.create_policy(input2)

        assert policy1.id != policy2.id
        assert policy1.id.startswith("POL-")
        assert policy2.id.startswith("POL-")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
