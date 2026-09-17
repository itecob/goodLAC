from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .client import (
    MAX_ADMIN_MESSAGE_BYTES,
    LacctlBoundaryError,
    LacctlClient,
    LacctlError,
    LacctlProtocolError,
    LacctlRequestRejected,
    LacctlUnavailable,
    canonical_json,
    strict_json_loads,
)

MAX_HUMAN_OUTPUT_BYTES = 262_144


class LacctlInputError(ValueError):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise LacctlInputError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="lacctl",
        description="Local Agent Controller owner administration client (P004 admin API v1)",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit canonical machine-readable JSON",
    )
    groups = parser.add_subparsers(dest="group", required=True)

    skills = groups.add_parser("skills", allow_abbrev=False)
    skills_cmd = skills.add_subparsers(dest="command", required=True)
    skills_cmd.add_parser("list", allow_abbrev=False)
    skill_show = skills_cmd.add_parser("show", allow_abbrev=False)
    skill_show.add_argument("application_id")
    skill_show.add_argument("skill_id")
    skill_show.add_argument("--revision", type=int)

    permissions = groups.add_parser("permissions", allow_abbrev=False)
    permissions_cmd = permissions.add_subparsers(dest="command", required=True)
    permissions_cmd.add_parser("list", allow_abbrev=False)
    permission_show = permissions_cmd.add_parser("show", allow_abbrev=False)
    permission_show.add_argument("--revision", type=int)
    permission_set = permissions_cmd.add_parser("set", allow_abbrev=False)
    permission_set.add_argument(
        "--file",
        required=True,
        dest="policy_file",
        help='JSON object containing exactly "rules" and "defaults" arrays',
    )
    permission_revoke = permissions_cmd.add_parser("revoke", allow_abbrev=False)
    permission_revoke.add_argument("kind", choices=("rule", "default"))
    permission_revoke.add_argument("id")

    pending = groups.add_parser("pending", allow_abbrev=False)
    pending_cmd = pending.add_subparsers(dest="command", required=True)
    pending_cmd.add_parser("list", allow_abbrev=False)
    pending_show = pending_cmd.add_parser("show", allow_abbrev=False)
    pending_show.add_argument("pending_id")
    pending_resolve = pending_cmd.add_parser("resolve", allow_abbrev=False)
    pending_resolve.add_argument("pending_id")
    pending_resolve.add_argument(
        "resolution",
        type=str.upper,
        choices=(
            "POLICY_UPDATED",
            "CAPABILITY_UPDATED",
            "POLICY_AND_CAPABILITY_UPDATED",
            "NO_CHANGE",
        ),
    )
    pending_dismiss = pending_cmd.add_parser("dismiss", allow_abbrev=False)
    pending_dismiss.add_argument("pending_id")

    emergency = groups.add_parser("emergency", allow_abbrev=False)
    emergency_cmd = emergency.add_subparsers(dest="command", required=True)
    emergency_cmd.add_parser("status", allow_abbrev=False)
    emergency_cmd.add_parser("pause", allow_abbrev=False)
    emergency_cmd.add_parser("resume", allow_abbrev=False)

    approvals = groups.add_parser("approvals", allow_abbrev=False)
    approvals_cmd = approvals.add_subparsers(dest="command", required=True)
    approvals_cmd.add_parser("list", allow_abbrev=False)
    approvals_show = approvals_cmd.add_parser("show", allow_abbrev=False)
    approvals_show.add_argument("decision_id")
    approvals_approve = approvals_cmd.add_parser("approve", allow_abbrev=False)
    approvals_approve.add_argument("decision_id")
    approvals_reject = approvals_cmd.add_parser("reject", allow_abbrev=False)
    approvals_reject.add_argument("decision_id")

    return parser


def _normalize_json_option(argv: list[str]) -> list[str]:
    count = argv.count("--json")
    if count > 1:
        raise LacctlInputError("--json may be specified at most once")
    if count == 1 and (not argv or argv[0] != "--json"):
        argv = [item for item in argv if item != "--json"]
        argv.insert(0, "--json")
    return argv


def _load_policy_file(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    try:
        info = path.stat()
    except OSError as exc:
        raise LacctlInputError("policy file is unavailable") from exc
    if not info.st_size or info.st_size > MAX_ADMIN_MESSAGE_BYTES:
        raise LacctlInputError("policy file size is invalid")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LacctlInputError("policy file could not be read") from exc
    if len(raw) != info.st_size or len(raw) > MAX_ADMIN_MESSAGE_BYTES:
        raise LacctlInputError("policy file changed while being read")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise LacctlInputError("policy file must be UTF-8 JSON") from exc
    try:
        material = strict_json_loads(text)
    except LacctlProtocolError as exc:
        raise LacctlInputError(str(exc)) from exc
    if not isinstance(material, dict) or set(material) != {"rules", "defaults"}:
        raise LacctlInputError('policy file must contain exactly "rules" and "defaults"')
    if not isinstance(material["rules"], list) or not isinstance(material["defaults"], list):
        raise LacctlInputError("policy rules/defaults must be arrays")
    # Ensure no non-JSON/NaN material can pass through.
    canonical_json(material)
    return material


def _operation(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    if args.group == "skills":
        if args.command == "list":
            return "skills.list", {}
        if args.command == "show":
            material: dict[str, Any] = {
                "application_id": args.application_id,
                "skill_id": args.skill_id,
            }
            if args.revision is not None:
                if args.revision < 1:
                    raise LacctlInputError("revision must be a positive integer")
                material["revision"] = args.revision
            return "skills.show", material

    if args.group == "permissions":
        if args.command == "list":
            return "permissions.list", {}
        if args.command == "show":
            material = {}
            if args.revision is not None:
                if args.revision < 1:
                    raise LacctlInputError("revision must be a positive integer")
                material["revision"] = args.revision
            return "permissions.show", material
        if args.command == "set":
            return "permissions.replace", _load_policy_file(args.policy_file)
        if args.command == "revoke":
            return "permissions.revoke", {"kind": args.kind.upper(), "id": args.id}

    if args.group == "pending":
        if args.command == "list":
            return "pending.list", {}
        if args.command == "show":
            return "pending.show", {"pending_id": args.pending_id}
        if args.command == "resolve":
            return "pending.resolve", {
                "pending_id": args.pending_id,
                "resolution": args.resolution,
            }
        if args.command == "dismiss":
            return "pending.dismiss", {"pending_id": args.pending_id}

    if args.group == "emergency":
        if args.command == "status":
            return "emergency.status", {}
        if args.command == "pause":
            return "emergency.pause", {}
        if args.command == "resume":
            return "emergency.resume", {}

    if args.group == "approvals":
        if args.command == "list":
            return "approvals.list", {}
        if args.command == "show":
            return "approvals.show", {"decision_id": args.decision_id}
        if args.command == "approve":
            return "approvals.approve", {"decision_id": args.decision_id}
        if args.command == "reject":
            return "approvals.reject", {"decision_id": args.decision_id}

    raise LacctlInputError("unsupported or ambiguous lacctl command")


def _human_skills(result: Any) -> str:
    if not isinstance(result, dict) or not isinstance(result.get("skills"), list):
        raise LacctlProtocolError("skills.list returned unexpected result shape")
    rows = result["skills"]
    if not rows:
        return "No skills.\n"
    lines = ["APPLICATION_ID\tSKILL_ID\tREVISION\tREGISTERED_AT_UTC"]
    for item in rows:
        if not isinstance(item, dict):
            raise LacctlProtocolError("skills.list item is malformed")
        lines.append(
            "\t".join(
                str(item.get(key, ""))
                for key in ("application_id", "skill_id", "revision", "registered_at_utc")
            )
        )
    return "\n".join(lines) + "\n"


def _human_permissions(result: Any) -> str:
    if not isinstance(result, dict):
        raise LacctlProtocolError("permissions result is malformed")
    rules = result.get("rules")
    defaults = result.get("defaults")
    if not isinstance(rules, list) or not isinstance(defaults, list):
        raise LacctlProtocolError("permissions result rules/defaults are malformed")
    lines = [
        f"revision: {result.get('revision', '')}",
        f"revision_id: {result.get('revision_id', '')}",
        f"policy_hash: {result.get('policy_hash', '')}",
        f"rules: {len(rules)}",
    ]
    lines.extend(f"RULE\t{canonical_json(item)}" for item in rules)
    lines.append(f"defaults: {len(defaults)}")
    lines.extend(f"DEFAULT\t{canonical_json(item)}" for item in defaults)
    return "\n".join(lines) + "\n"


def _human_pending(result: Any) -> str:
    if not isinstance(result, dict) or not isinstance(result.get("pending"), list):
        raise LacctlProtocolError("pending.list returned unexpected result shape")
    rows = result["pending"]
    if not rows:
        return "No pending permission requests.\n"
    lines = [
        "PENDING_ID\tSTATUS\tCOUNT\tAPPLICATION_ID\tSKILL_ID\tACTION\tRESOURCE\tREASON"
    ]
    for item in rows:
        if not isinstance(item, dict):
            raise LacctlProtocolError("pending.list item is malformed")
        lines.append(
            "\t".join(
                str(item.get(key, ""))
                for key in (
                    "pending_id",
                    "administrative_status",
                    "count",
                    "application_id",
                    "skill_id",
                    "action",
                    "resource",
                    "reason",
                )
            )
        )
    return "\n".join(lines) + "\n"


def _human_approvals(result: Any) -> str:
    if not isinstance(result, dict) or not isinstance(result.get("approvals"), list):
        raise LacctlProtocolError("approvals.list returned unexpected result shape")
    rows = result["approvals"]
    if not rows:
        return "No approval candidates.\n"
    lines = ["DECISION_ID\tAPPROVAL\tEXECUTION_STATE\tREQUEST_ID\tACTION\tRESOURCE"]
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("decision"), dict) or not isinstance(item.get("request"), dict):
            raise LacctlProtocolError("approvals.list item is malformed")
        approval = item.get("approval")
        approval_value = "PENDING" if approval is None else str(approval.get("decision", "")) if isinstance(approval, dict) else "INVALID"
        lines.append(
            "\t".join(
                (
                    str(item["decision"].get("decision_id", "")),
                    approval_value,
                    str(item.get("execution_state") or ""),
                    str(item["request"].get("request_id", "")),
                    str(item["request"].get("action", "")),
                    str(item["request"].get("resource", "")),
                )
            )
        )
    return "\n".join(lines) + "\n"


def _render_human(operation: str, result: Any) -> str:
    if operation == "skills.list":
        rendered = _human_skills(result)
    elif operation in {"permissions.list", "permissions.show", "permissions.replace", "permissions.revoke"}:
        rendered = _human_permissions(result)
    elif operation == "pending.list":
        rendered = _human_pending(result)
    elif operation == "approvals.list":
        rendered = _human_approvals(result)
    else:
        try:
            rendered = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        except (TypeError, ValueError) as exc:
            raise LacctlProtocolError("administrator result is not JSON-renderable") from exc
    if len(rendered.encode("utf-8")) > MAX_HUMAN_OUTPUT_BYTES:
        raise LacctlProtocolError("human-readable output exceeds bounded display size; use --json")
    return rendered


def _json_error(code: str, message: str) -> str:
    return canonical_json(
        {
            "schema": "lac.lacctl-error/v1",
            "ok": False,
            "error": {"code": code, "message": message},
        }
    ) + "\n"


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in raw
    try:
        raw = _normalize_json_option(raw)
        args = _parser().parse_args(raw)
        operation, arguments = _operation(args)
        result = LacctlClient().call(operation, arguments)
        output = canonical_json(result) + "\n" if args.json else _render_human(operation, result)
        sys.stdout.write(output)
        return 0
    except LacctlRequestRejected as exc:
        if json_mode:
            sys.stdout.write(_json_error(exc.code, str(exc)))
        else:
            sys.stderr.write(f"lacctl: {exc.code}: {exc}\n")
        return 3
    except (LacctlUnavailable, LacctlBoundaryError) as exc:
        if json_mode:
            sys.stdout.write(_json_error(exc.code, str(exc)))
        else:
            sys.stderr.write(f"lacctl: {exc.code}: {exc}\n")
        return 4
    except (LacctlProtocolError, LacctlInputError, LacctlError) as exc:
        code = getattr(exc, "code", "INVALID_LACCTL_INPUT")
        if json_mode:
            sys.stdout.write(_json_error(code, str(exc)))
        else:
            sys.stderr.write(f"lacctl: {code}: {exc}\n")
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
