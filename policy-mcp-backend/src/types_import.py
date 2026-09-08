"""
Types and dataclasses for the insurance policy system
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Policy:
    """Insurance policy representation"""
    id: str
    customer_id: str
    policy_type: Literal["auto", "home", "health", "life"]
    start_date: str
    end_date: str
    premium: float
    status: Literal["active", "inactive", "cancelled"]
    coverage_options: list[str] = field(default_factory=list)
    deductible: float = 0
    policy_limit: float = 0


@dataclass
class CoverageOption:
    """Available insurance coverage option"""
    id: str
    name: str
    description: str
    policy_types: list[str] = field(default_factory=list)
    base_price: float = 0
    coverage_amount: float = 0


@dataclass
class Claim:
    """Insurance claim representation"""
    id: str
    policy_id: str
    claim_date: str
    claim_type: str
    amount: float
    status: Literal["submitted", "processing", "approved", "rejected"]
    description: str


@dataclass
class PolicyHolder:
    """Fictional policy holder profile for demos"""
    customer_id: str
    name: str
    phone_number: str
    address: str
    ssn: str
    passport_number: str
    annual_income: float
    family_members: int


@dataclass
class AgentLogin:
    """Demo Policy Agent login account"""
    username: str
    role: Literal["consumer", "supervisor", "admin"]
    display_name: str
    customer_id: str | None = None


@dataclass
class AgentPersonalInfo:
    """Fictional personal profile for demo agent users"""
    username: str
    role: Literal["consumer", "supervisor", "admin"]
    name: str
    phone_number: str
    address: str
    ssn: str
    passport_number: str
    annual_income: float
    family_members: int
    customer_id: str | None = None


@dataclass
class CreatePolicyInput:
    """Input for creating a new policy"""
    customer_id: str
    policy_type: Literal["auto", "home", "health", "life"]
    start_date: str
    end_date: str
    premium: float
    coverage_options: list[str] = field(default_factory=list)
    deductible: float = 0
    policy_limit: float = 0


@dataclass
class SubmitClaimInput:
    """Input for submitting a claim"""
    policy_id: str
    claim_type: str
    amount: float
    description: str
