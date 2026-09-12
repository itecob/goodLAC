"""Authority-core domain types."""

from .approval import (
    APPROVAL_SCHEMA,
    Approval,
    ApprovalDecision,
    ApprovalError,
    ApprovalScope,
    UnsupportedApprovalSchema,
)
from .effect_receipt import (
    EFFECT_EXECUTION_SCHEMA,
    EFFECT_RECEIPT_SCHEMA,
    EffectExecution,
    EffectExecutionState,
    EffectOutcome,
    EffectReceipt,
    EffectReceiptError,
    UnsupportedEffectReceiptSchema,
    canonical_result_json,
    deterministic_receipt_id,
    result_hash_for_json,
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
    "APPROVAL_SCHEMA", "Approval", "ApprovalDecision", "ApprovalError", "ApprovalScope",
    "UnsupportedApprovalSchema", "EFFECT_EXECUTION_SCHEMA", "EFFECT_RECEIPT_SCHEMA",
    "EffectExecution", "EffectExecutionState", "EffectOutcome", "EffectReceipt",
    "EffectReceiptError", "UnsupportedEffectReceiptSchema", "canonical_result_json",
    "deterministic_receipt_id", "result_hash_for_json", "EXECUTION_LEASE_SCHEMA",
    "MAX_EXECUTION_LEASE_SECONDS", "ExecutionLease", "ExecutionLeaseError",
    "UnsupportedExecutionLeaseSchema", "EFFECT_REQUEST_SCHEMA", "EffectRequest",
    "EffectRequestError", "UnsupportedEffectRequestSchema", "canonical_json",
    "POLICY_DECISION_SCHEMA", "POLICY_PRECEDENCE", "PolicyDecision",
    "PolicyDecisionError", "PolicyDecisionValue", "UnsupportedPolicyDecisionSchema",
]
