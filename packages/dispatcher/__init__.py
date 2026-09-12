"""Deterministic pre-dispatch authority boundary."""

from .dispatcher import (
    DispatchAdapterError,
    DispatchApprovalRequired,
    DispatchAuthorityError,
    DispatchDenied,
    DispatchError,
    DispatchPaused,
    DispatchRequestExpired,
    Dispatcher,
    EffectAdapter,
)

__all__ = [
    "DispatchAdapterError",
    "DispatchApprovalRequired",
    "DispatchAuthorityError",
    "DispatchDenied",
    "DispatchError",
    "DispatchPaused",
    "DispatchRequestExpired",
    "Dispatcher",
    "EffectAdapter",
]
