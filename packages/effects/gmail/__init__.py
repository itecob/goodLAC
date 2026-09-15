"""Typed Gmail effects for the Phase 4 Chief of Staff pilot."""

from .adapter import (
    GMAIL_ACTIONS,
    GMAIL_ADAPTER_ID,
    GMAIL_ARCHIVE_ACTION,
    GMAIL_DELETE_ACTION,
    GMAIL_DRAFT_ACTION,
    GMAIL_READ_ACTION,
    GMAIL_RESULT_SCHEMA,
    GMAIL_SEARCH_ACTION,
    GMAIL_SEND_ACTION,
    GmailEffectAdapter,
    GmailEffectError,
    GmailEffectResult,
    GmailMessageInput,
    GmailTransport,
    GmailTransportFactory,
)
from .google_api import (
    GMAIL_API_BASE,
    GoogleGmailTransport,
    GoogleGmailTransportError,
    GoogleGmailTransportFactory,
)
from .policy import GMAIL_DEFAULT_POLICY, gmail_policy_provider, gmail_policy_rules

__all__ = [
    "GMAIL_ACTIONS",
    "GMAIL_ADAPTER_ID",
    "GMAIL_ARCHIVE_ACTION",
    "GMAIL_DEFAULT_POLICY",
    "GMAIL_API_BASE",
    "GMAIL_DELETE_ACTION",
    "GMAIL_DRAFT_ACTION",
    "GMAIL_READ_ACTION",
    "GMAIL_RESULT_SCHEMA",
    "GMAIL_SEARCH_ACTION",
    "GMAIL_SEND_ACTION",
    "GmailEffectAdapter",
    "GmailEffectError",
    "GmailEffectResult",
    "GmailMessageInput",
    "GmailTransport",
    "GmailTransportFactory",
    "GoogleGmailTransport",
    "GoogleGmailTransportError",
    "GoogleGmailTransportFactory",
    "gmail_policy_provider",
    "gmail_policy_rules",
]
