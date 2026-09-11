"""Authority-core domain types."""

from .approval import (
    APPROVAL_SCHEMA,
    Approval,
    ApprovalDecision,
    ApprovalError,
    ApprovalScope,
    UnsupportedApprovalSchema,
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
