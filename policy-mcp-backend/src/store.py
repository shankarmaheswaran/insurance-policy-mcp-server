"""
In-memory data store for policies and claims
In a real application, this would use a database
"""

from datetime import datetime
try:
    from .types_import import (
        AgentLogin,
        Claim,
        CoverageOption,
        CreatePolicyInput,
        Policy,
        PolicyHolder,
        SubmitClaimInput,
    )
except ImportError:
    from types_import import (
        AgentLogin,
        Claim,
        CoverageOption,
        CreatePolicyInput,
        Policy,
        PolicyHolder,
        SubmitClaimInput,
    )


class PolicyStore:
    """Store for managing insurance policies, claims, and coverage options"""

    def __init__(self) -> None:
        self.policies: dict[str, Policy] = {}
        self.claims: dict[str, Claim] = {}
        self.coverage_options: dict[str, CoverageOption] = {}
        self.policy_holders: dict[str, PolicyHolder] = {}
        self.agent_logins: dict[str, AgentLogin] = {}
        self.policy_id_counter = 1000
        self.claim_id_counter = 5000
        self._initialize_sample_data()

    def _initialize_sample_data(self) -> None:
        """Initialize store with sample data"""
        policy_holders = [
            PolicyHolder("CUST-001", "Avery Johnson", "555-0101", "101 Maple Street, Sacramento, CA 95814", "FAKE-SSN-1001", "FAKE-PASS-A1001", 82000, 3),
            PolicyHolder("CUST-002", "Morgan Lee", "555-0102", "220 Oak Avenue, San Diego, CA 92101", "FAKE-SSN-1002", "FAKE-PASS-A1002", 104000, 4),
            PolicyHolder("CUST-003", "Jordan Smith", "555-0103", "315 Pine Road, Fresno, CA 93721", "FAKE-SSN-1003", "FAKE-PASS-A1003", 67000, 2),
            PolicyHolder("CUST-004", "Priya Raman", "555-0104", "48 Cedar Lane, Irvine, CA 92602", "FAKE-SSN-1004", "FAKE-PASS-A1004", 128000, 4),
            PolicyHolder("CUST-005", "Carlos Rivera", "555-0105", "780 Mission Drive, San Jose, CA 95112", "FAKE-SSN-1005", "FAKE-PASS-A1005", 93000, 5),
            PolicyHolder("CUST-006", "Taylor Brown", "555-0106", "19 Sunset Court, Oakland, CA 94607", "FAKE-SSN-1006", "FAKE-PASS-A1006", 76000, 1),
            PolicyHolder("CUST-007", "Nina Patel", "555-0107", "402 Valley Way, Pasadena, CA 91101", "FAKE-SSN-1007", "FAKE-PASS-A1007", 116000, 3),
            PolicyHolder("CUST-008", "Ethan Wilson", "555-0108", "909 Harbor Boulevard, Long Beach, CA 90802", "FAKE-SSN-1008", "FAKE-PASS-A1008", 59000, 2),
            PolicyHolder("CUST-009", "Sophia Chen", "555-0109", "67 Sierra Place, Santa Clara, CA 95050", "FAKE-SSN-1009", "FAKE-PASS-A1009", 141000, 4),
            PolicyHolder("CUST-010", "Marcus Davis", "555-0110", "125 Redwood Terrace, Los Angeles, CA 90012", "FAKE-SSN-1010", "FAKE-PASS-A1010", 88000, 3),
        ]

        for holder in policy_holders:
            self.policy_holders[holder.customer_id] = holder

        agent_logins = [
            AgentLogin(f"consumer{index:02d}", "consumer", holder.name, holder.customer_id)
            for index, holder in enumerate(policy_holders, start=1)
        ]
        agent_logins.extend(
            [
                AgentLogin("supervisor01", "supervisor", "Dana Brooks"),
                AgentLogin("supervisor02", "supervisor", "Riley Foster"),
                AgentLogin("supervisor03", "supervisor", "Casey Nguyen"),
                AgentLogin("admin01", "admin", "System Administrator"),
            ]
        )

        for login in agent_logins:
            self.agent_logins[login.username] = login

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

        # Sample policies: every seeded customer has at least one policy.
        policies = [
            Policy("POL-1000", "CUST-001", "auto", "2024-01-01", "2025-01-01", 1200, "active", ["cov-001", "cov-002"], 500, 100000),
            Policy("POL-1001", "CUST-002", "home", "2024-03-15", "2025-03-15", 1800, "active", ["cov-003"], 1000, 500000),
            Policy("POL-1002", "CUST-003", "health", "2024-04-01", "2025-04-01", 950, "active", ["cov-004"], 250, 100000),
            Policy("POL-1003", "CUST-004", "life", "2024-05-01", "2025-05-01", 1100, "active", [], 0, 300000),
            Policy("POL-1004", "CUST-005", "auto", "2024-06-01", "2025-06-01", 1350, "active", ["cov-001"], 750, 125000),
            Policy("POL-1005", "CUST-006", "home", "2024-07-01", "2025-07-01", 1600, "active", ["cov-003"], 1200, 450000),
            Policy("POL-1006", "CUST-007", "health", "2024-08-01", "2025-08-01", 1025, "active", ["cov-004"], 300, 125000),
            Policy("POL-1007", "CUST-008", "life", "2024-09-01", "2025-09-01", 875, "active", [], 0, 200000),
            Policy("POL-1008", "CUST-009", "auto", "2024-10-01", "2025-10-01", 1450, "active", ["cov-001", "cov-002"], 500, 150000),
            Policy("POL-1009", "CUST-010", "home", "2024-11-01", "2025-11-01", 1725, "active", ["cov-003"], 1000, 550000),
        ]

        for policy in policies:
            self.policies[policy.id] = policy
        self.policy_id_counter = 1010

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

    def update_policy(self, policy_id: str, updates: dict) -> Policy | None:
        """Update editable policy fields"""
        policy = self.policies.get(policy_id)
        if not policy:
            return None

        editable_fields = {
            "policy_type",
            "start_date",
            "end_date",
            "premium",
            "coverage_options",
            "deductible",
            "policy_limit",
        }
        for field_name, value in updates.items():
            if field_name in editable_fields:
                setattr(policy, field_name, value)
        return policy

    def renew_policy(self, policy_id: str, end_date: str, premium: float | None = None) -> Policy | None:
        """Renew a policy by extending its end date and keeping it active"""
        policy = self.policies.get(policy_id)
        if not policy:
            return None

        policy.end_date = end_date
        if premium is not None:
            policy.premium = premium
        policy.status = "active"
        return policy

    def change_policy_status(self, policy_id: str, status: str) -> Policy | None:
        """Change policy status to an allowed non-delete state"""
        if status not in {"active", "inactive", "cancelled"}:
            raise ValueError("Invalid policy status")

        policy = self.policies.get(policy_id)
        if not policy:
            return None

        policy.status = status
        return policy

    def get_policy(self, policy_id: str) -> Policy | None:
        """Get a policy by ID"""
        return self.policies.get(policy_id)

    def get_policy_holder(self, customer_id: str) -> PolicyHolder | None:
        """Get a fictional policy holder by customer ID"""
        return self.policy_holders.get(customer_id)

    def list_policy_holders(self) -> list[PolicyHolder]:
        """List all fictional policy holders sorted by customer ID"""
        return sorted(self.policy_holders.values(), key=lambda holder: holder.customer_id)

    def list_agent_logins(self, role: str | None = None) -> list[AgentLogin]:
        """List demo Policy Agent login accounts, optionally filtered by role"""
        logins = list(self.agent_logins.values())
        if role:
            logins = [login for login in logins if login.role == role]
        return sorted(logins, key=lambda login: login.username)

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
