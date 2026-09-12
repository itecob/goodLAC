"""Authority-core domain types."""

from .approval import (
    APPROVAL_SCHEMA,
    Approval,
    ApprovalDecision,
    ApprovalError,
    ApprovalScope,
    UnsupportedApprovalSchema,
)
from .execution_lease import (
    EXECUTION_LEASE_SCHEMA,
    MAX_EXECUTION_LEASE_SECONDS,
    ExecutionLease,
    ExecutionLeaseError,
    UnsupportedExecutionLeaseSchema,
)
from .effect_request import (
    EFFECT_REQUEST_SCHEMA,
    EffectRequest,
    EffectRequestError,
    UnsupportedEffectRequestSchema,
    canonical_json,
)
from .policy import (
    POLICY_DECISION_SCHEMA,
    POLICY_PRECEDENCE,
    PolicyDecision,
    PolicyDecisionError,
    PolicyDecisionValue,
    UnsupportedPolicyDecisionSchema,
)

__all__ = [
    "APPROVAL_SCHEMA",
    "Approval",
    "ApprovalDecision",
    "ApprovalError",
    "ApprovalScope",
    "UnsupportedApprovalSchema",
    "EXECUTION_LEASE_SCHEMA",
    "MAX_EXECUTION_LEASE_SECONDS",
    "ExecutionLease",
    "ExecutionLeaseError",
    "UnsupportedExecutionLeaseSchema",
    "EFFECT_REQUEST_SCHEMA",
    "EffectRequest",
    "EffectRequestError",
    "UnsupportedEffectRequestSchema",
    "canonical_json",
    "POLICY_DECISION_SCHEMA",
    "POLICY_PRECEDENCE",
    "PolicyDecision",
    "PolicyDecisionError",
    "PolicyDecisionValue",
    "UnsupportedPolicyDecisionSchema",
]
