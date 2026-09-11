from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, runtime_checkable

from packages.core import (
    EffectRequest,
    POLICY_PRECEDENCE,
    PolicyDecision,
    PolicyDecisionValue,
)


class PolicyConfigurationError(ValueError):
    """The local policy snapshot is malformed or internally inconsistent."""


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PolicyConfigurationError(f"{field} must be a non-empty trimmed string")
    return value


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    principal_id: str
    agent_id: str
    action: str
    resource: str
    decision: PolicyDecisionValue

    @classmethod
    def create(
        cls,
        *,
        rule_id: str,
        principal_id: str,
        agent_id: str,
        action: str,
        resource: str,
        decision: PolicyDecisionValue | str,
    ) -> "PolicyRule":
        try:
            decision_value = PolicyDecisionValue(decision)
        except (TypeError, ValueError) as exc:
            raise PolicyConfigurationError(
                f"unsupported policy rule decision: {decision!r}"
            ) from exc
        return cls(
            rule_id=_required_text(rule_id, "rule_id"),
            principal_id=_required_text(principal_id, "principal_id"),
            agent_id=_required_text(agent_id, "agent_id"),
            action=_required_text(action, "action"),
            resource=_required_text(resource, "resource"),
            decision=decision_value,
        )


@runtime_checkable
class PolicyDecisionProvider(Protocol):
    @property
    def policy_revision(self) -> str:
        ...

    def evaluate(
        self,
        request: EffectRequest,
        *,
        decision_id: str,
        evaluated_at: str,
    ) -> PolicyDecision:
        ...


class LocalPolicyDecisionProvider:
    """Small exact-match Phase 1 provider; unknown authority always fails closed."""

    def __init__(
        self,
        *,
        revision: str,
        known_principals: Iterable[str],
        known_agents: Iterable[str],
        known_actions: Iterable[str],
        known_resources: Iterable[str],
        rules: Iterable[PolicyRule],
    ) -> None:
        self._policy_revision = _required_text(revision, "revision")
        self._known_principals = self._normalize_registry(
            known_principals, "known_principals"
        )
        self._known_agents = self._normalize_registry(known_agents, "known_agents")
        self._known_actions = self._normalize_registry(known_actions, "known_actions")
        self._known_resources = self._normalize_registry(
            known_resources, "known_resources"
        )
        self._rules = tuple(sorted(tuple(rules), key=lambda rule: rule.rule_id))
        self._validate_rules()

    @staticmethod
    def _normalize_registry(values: Iterable[str], field: str) -> frozenset[str]:
        try:
            normalized = frozenset(_required_text(value, field) for value in values)
        except TypeError as exc:
            raise PolicyConfigurationError(f"{field} must be iterable") from exc
        return normalized

    def _validate_rules(self) -> None:
        seen_ids: set[str] = set()
        for rule in self._rules:
            if not isinstance(rule, PolicyRule):
                raise PolicyConfigurationError("rules must contain PolicyRule values")
            if rule.rule_id in seen_ids:
                raise PolicyConfigurationError(f"duplicate rule_id: {rule.rule_id}")
            seen_ids.add(rule.rule_id)
            checks = (
                (rule.principal_id, self._known_principals, "principal"),
                (rule.agent_id, self._known_agents, "agent"),
                (rule.action, self._known_actions, "action"),
                (rule.resource, self._known_resources, "resource"),
            )
            for value, registry, label in checks:
                if value not in registry:
                    raise PolicyConfigurationError(
                        f"rule {rule.rule_id!r} references unknown {label} {value!r}"
                    )

    @property
    def policy_revision(self) -> str:
        return self._policy_revision

    def evaluate(
        self,
        request: EffectRequest,
        *,
        decision_id: str,
        evaluated_at: str,
    ) -> PolicyDecision:
        if not isinstance(request, EffectRequest):
            raise PolicyConfigurationError("request must be a canonical EffectRequest")

        unknown_codes: list[str] = []
        if request.principal_id not in self._known_principals:
            unknown_codes.append("UNKNOWN_PRINCIPAL")
        if request.agent_id not in self._known_agents:
            unknown_codes.append("UNKNOWN_AGENT")
        if request.action not in self._known_actions:
            unknown_codes.append("UNKNOWN_ACTION")
        if request.resource not in self._known_resources:
            unknown_codes.append("UNKNOWN_RESOURCE")

        if unknown_codes:
            return self._decision(
                request,
                decision_id=decision_id,
                evaluated_at=evaluated_at,
                decision=PolicyDecisionValue.DENY,
                reason_codes=unknown_codes,
            )

        matching = tuple(
            rule
            for rule in self._rules
            if rule.principal_id == request.principal_id
            and rule.agent_id == request.agent_id
            and rule.action == request.action
            and rule.resource == request.resource
        )
        if not matching:
            return self._decision(
                request,
                decision_id=decision_id,
                evaluated_at=evaluated_at,
                decision=PolicyDecisionValue.DENY,
                reason_codes=("NO_MATCHING_RULE",),
            )

        strongest = max(matching, key=lambda rule: POLICY_PRECEDENCE[rule.decision]).decision
        reason_codes = [f"MATCHED_RULE:{rule.rule_id}" for rule in matching]
        reason_codes.append(f"DECISION:{strongest.value}")
        distinct = {rule.decision for rule in matching}
        if len(distinct) > 1:
            if strongest is PolicyDecisionValue.DENY:
                reason_codes.append("DENY_PRECEDENCE_APPLIED")
            elif strongest is PolicyDecisionValue.REQUIRE_APPROVAL:
                reason_codes.append("APPROVAL_PRECEDENCE_APPLIED")

        return self._decision(
            request,
            decision_id=decision_id,
            evaluated_at=evaluated_at,
            decision=strongest,
            reason_codes=reason_codes,
        )

    def _decision(
        self,
        request: EffectRequest,
        *,
        decision_id: str,
        evaluated_at: str,
        decision: PolicyDecisionValue,
        reason_codes: Iterable[str],
    ) -> PolicyDecision:
        return PolicyDecision.create(
            decision_id=decision_id,
            request_id=request.request_id,
            decision=decision,
            policy_revision=self._policy_revision,
            reason_codes=tuple(reason_codes),
            evaluated_at=evaluated_at,
            canonical_request_hash=request.canonical_hash,
        )
