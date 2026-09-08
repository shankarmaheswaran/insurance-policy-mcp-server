"""
In-memory data store for policies and claims
In a real application, this would use a database
"""

from datetime import datetime
from types_import import Policy, CoverageOption, Claim, CreatePolicyInput, SubmitClaimInput


class PolicyStore:
    """Store for managing insurance policies, claims, and coverage options"""

    def __init__(self) -> None:
        self.policies: dict[str, Policy] = {}
        self.claims: dict[str, Claim] = {}
        self.coverage_options: dict[str, CoverageOption] = {}
        self.policy_id_counter = 1000
        self.claim_id_counter = 5000
        self._initialize_sample_data()

    def _initialize_sample_data(self) -> None:
        """Initialize store with sample data"""
        # Sample coverage options
        coverage_options = [
            CoverageOption(
                id="cov-001",
                name="Comprehensive Coverage",
                description="Covers damage from non-collision incidents",
                policy_types=["auto"],
                base_price=150,
                coverage_amount=50000,
            ),
            CoverageOption(
                id="cov-002",
                name="Collision Coverage",
                description="Covers damage from collisions",
                policy_types=["auto"],
                base_price=200,
                coverage_amount=75000,
            ),
            CoverageOption(
                id="cov-003",
                name="Homeowners Liability",
                description="Protects against liability claims",
                policy_types=["home"],
                base_price=300,
                coverage_amount=300000,
            ),
            CoverageOption(
                id="cov-004",
                name="Medical Coverage",
                description="Covers basic medical expenses",
                policy_types=["health"],
                base_price=100,
                coverage_amount=100000,
            ),
        ]

        for opt in coverage_options:
            self.coverage_options[opt.id] = opt

        # Sample policies
        policy1 = Policy(
            id="POL-1000",
            customer_id="CUST-001",
            policy_type="auto",
            start_date="2024-01-01",
            end_date="2025-01-01",
            premium=1200,
            status="active",
            coverage_options=["cov-001", "cov-002"],
            deductible=500,
            policy_limit=100000,
        )

        policy2 = Policy(
            id="POL-1001",
            customer_id="CUST-002",
            policy_type="home",
            start_date="2024-03-15",
            end_date="2025-03-15",
            premium=1800,
            status="active",
            coverage_options=["cov-003"],
            deductible=1000,
            policy_limit=500000,
        )

        self.policies[policy1.id] = policy1
        self.policies[policy2.id] = policy2

        # Sample claims
        claim1 = Claim(
            id="CLM-5000",
            policy_id="POL-1000",
            claim_date="2024-06-15",
            claim_type="collision",
            amount=5000,
            status="approved",
            description="Minor collision damage",
        )

        self.claims[claim1.id] = claim1

    def create_policy(self, input_data: CreatePolicyInput) -> Policy:
        """Create a new policy"""
        policy_id = f"POL-{self.policy_id_counter}"
        self.policy_id_counter += 1

        policy = Policy(
            id=policy_id,
            customer_id=input_data.customer_id,
            policy_type=input_data.policy_type,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            premium=input_data.premium,
            status="active",
            coverage_options=input_data.coverage_options,
            deductible=input_data.deductible,
            policy_limit=input_data.policy_limit,
        )
        self.policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Policy | None:
        """Get a policy by ID"""
        return self.policies.get(policy_id)

    def list_policies(self, customer_id: str | None = None) -> list[Policy]:
        """List all policies, optionally filtered by customer, in reverse chronological order"""
        policies = list(self.policies.values())
        if customer_id:
            policies = [p for p in policies if p.customer_id == customer_id]
        # Sort by policy ID in descending order (newer policies have higher numbers)
        policies.sort(key=lambda p: int(p.id.split('-')[1]), reverse=True)
        return policies

    def get_coverage_option(self, coverage_id: str) -> CoverageOption | None:
        """Get a coverage option by ID"""
        return self.coverage_options.get(coverage_id)

    def list_coverage_options(self, policy_type: str | None = None) -> list[CoverageOption]:
        """List all coverage options, optionally filtered by policy type"""
        options = list(self.coverage_options.values())
        if policy_type:
            return [o for o in options if policy_type in o.policy_types]
        return options

    def submit_claim(self, input_data: SubmitClaimInput) -> Claim:
        """Submit a new claim"""
        claim_id = f"CLM-{self.claim_id_counter}"
        self.claim_id_counter += 1

        claim = Claim(
            id=claim_id,
            policy_id=input_data.policy_id,
            claim_date=datetime.now().strftime("%Y-%m-%d"),
            claim_type=input_data.claim_type,
            amount=input_data.amount,
            status="submitted",
            description=input_data.description,
        )
        self.claims[claim_id] = claim
        return claim

    def get_claim(self, claim_id: str) -> Claim | None:
        """Get a claim by ID"""
        return self.claims.get(claim_id)

    def list_claims(self, policy_id: str | None = None) -> list[Claim]:
        """List all claims, optionally filtered by policy, in reverse chronological order"""
        claims = list(self.claims.values())
        if policy_id:
            claims = [c for c in claims if c.policy_id == policy_id]
        # Sort by claim ID in descending order (newer claims have higher numbers)
        claims.sort(key=lambda c: int(c.id.split('-')[1]), reverse=True)
        return claims
