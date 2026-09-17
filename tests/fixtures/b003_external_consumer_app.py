#!/usr/bin/env python3
"""Stdlib-only external application fixture; intentionally imports no LAC package."""

import argparse
import json
import sys

APP_ID = "b003-external-app"
SKILL_ID = "notes"
RESOURCE = "notes:workspace"


def manifest():
    resource = {"type": "notes.local", "selectors": [RESOURCE]}
    arg_schema = {
        "type": "object",
        "properties": {"note_id": {"type": "string", "minLength": 1, "maxLength": 128}},
        "required": ["note_id"],
        "additionalProperties": False,
    }
    return {
        "schema": "lac.capability-manifest/v1",
        "manifest_version": 1,
        "application_id": APP_ID,
        "skill_id": SKILL_ID,
        "actions": [
            {
                "action": "notes.read",
                "resource": resource,
                "arguments": arg_schema,
                "security_properties": ["read_only"],
            },
            {
                "action": "notes.write",
                "resource": resource,
                "arguments": arg_schema,
                "security_properties": ["local_mutation"],
            },
            {
                "action": "notes.publish",
                "resource": resource,
                "arguments": arg_schema,
                "security_properties": ["external_communication", "external_mutation", "network_egress"],
            },
        ],
    }


def request(args):
    return {
        "schema": "lac.external-consumer-request/v1",
        "request_id": args.request_id,
        "run_id": args.run_id,
        "action": args.action,
        "resource": RESOURCE,
        "arguments": {"note_id": args.note_id},
        "idempotency_key": args.idempotency_key,
    }


def consume():
    raw = json.load(sys.stdin)
    if raw.get("schema") != "lac.external-consumer-response/v1":
        raise SystemExit("invalid response schema")
    outcome = raw.get("authority_outcome")
    if outcome not in {"ALLOW", "REQUIRE_APPROVAL", "DENY"}:
        raise SystemExit("invalid authority outcome")
    if outcome == "ALLOW":
        if raw.get("execution_state") != "SUCCEEDED":
            raise SystemExit("ALLOW response lacks successful execution")
        if not isinstance(raw.get("result"), dict):
            raise SystemExit("ALLOW response lacks typed result")
        receipt = raw.get("receipt")
        if not isinstance(receipt, dict) or not receipt.get("receipt_id"):
            raise SystemExit("ALLOW response lacks receipt")
    print("B003_CONSUMER_ACCEPTED=1")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("declare")
    req = sub.add_parser("request")
    req.add_argument("--request-id", required=True)
    req.add_argument("--run-id", default="run:b003")
    req.add_argument("--action", required=True)
    req.add_argument("--note-id", required=True)
    req.add_argument("--idempotency-key", required=True)
    sub.add_parser("consume")
    args = parser.parse_args()
    if args.command == "declare":
        json.dump(manifest(), sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return
    if args.command == "request":
        json.dump(request(args), sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return
    consume()


if __name__ == "__main__":
    main()
