from __future__ import annotations

from packages.policy import LocalPolicyDecisionProvider, PolicyRule

from .adapter import (
    GMAIL_ACTIONS,
    GMAIL_ARCHIVE_ACTION,
    GMAIL_DELETE_ACTION,
    GMAIL_DRAFT_ACTION,
    GMAIL_READ_ACTION,
    GMAIL_SEARCH_ACTION,
    GMAIL_SEND_ACTION,
)


GMAIL_DEFAULT_POLICY = {
    GMAIL_SEARCH_ACTION: "ALLOW",
    GMAIL_READ_ACTION: "ALLOW",
    GMAIL_DRAFT_ACTION: "ALLOW",
    GMAIL_SEND_ACTION: "REQUIRE_APPROVAL",
    GMAIL_ARCHIVE_ACTION: "REQUIRE_APPROVAL",
    GMAIL_DELETE_ACTION: "DENY",
}


def gmail_policy_rules(*, principal_id: str, agent_id: str, resource: str) -> tuple[PolicyRule, ...]:
    return tuple(
        PolicyRule.create(
            rule_id=f"gmail:{action}:{decision.lower()}",
            principal_id=principal_id,
            agent_id=agent_id,
            action=action,
            resource=resource,
            decision=decision,
        )
        for action, decision in sorted(GMAIL_DEFAULT_POLICY.items())
    )


def gmail_policy_provider(
    *,
    principal_id: str,
    agent_id: str,
    resource: str = "email-account:primary",
    revision: str = "policy:gmail:chief-of-staff:v1",
) -> LocalPolicyDecisionProvider:
    return LocalPolicyDecisionProvider(
        revision=revision,
        known_principals={principal_id},
        known_agents={agent_id},
        known_actions=GMAIL_ACTIONS,
        known_resources={resource},
        rules=gmail_policy_rules(
            principal_id=principal_id,
            agent_id=agent_id,
            resource=resource,
        ),
    )
