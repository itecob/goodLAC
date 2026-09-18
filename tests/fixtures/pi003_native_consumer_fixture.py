#!/usr/bin/env python3
"""Stdlib-only PI003 fixture. It has no LAC imports and no administrator capability."""

from __future__ import annotations

import argparse
import json
import sys

REQUEST_SCHEMA = "lac.external-consumer-request/v1"
RESULT_SCHEMA = "lac.native-local-consumer-result/v1"
STATUS_SCHEMA = "lac.native-local-consumer-continuation-status/v1"
RESUME_SCHEMA = "lac.native-local-consumer-resume/v1"


def declaration():
    return {
        "schema": "lac.capability-manifest/v1",
        "manifest_version": 1,
        "application_id": "pi003-native-fixture",
        "skill_id": "notes",
        "actions": [
            {
                "action": "notes.write",
                "resource": {
                    "type": "notes.local",
                    "selectors": ["notes:workspace"],
                },
                "arguments": {
                    "type": "object",
                    "properties": {
                        "note_id": {"type": "string", "minLength": 1, "maxLength": 128},
                        "content": {"type": "string", "minLength": 0, "maxLength": 4096},
                    },
                    "required": ["note_id", "content"],
                    "additionalProperties": False,
                },
                "security_properties": ["local_mutation"],
            }
        ],
    }


def request(args):
    return {
        "schema": REQUEST_SCHEMA,
        "request_id": args.request_id,
        "run_id": "run:pi003-native-fixture",
        "action": "notes.write",
        "resource": "notes:workspace",
        "arguments": {"note_id": args.note_id, "content": args.content},
        "idempotency_key": args.idempotency_key,
    }


def consume(schema, marker):
    material = json.load(sys.stdin)
    if not isinstance(material, dict) or material.get("schema") != schema:
        raise SystemExit(f"unexpected schema: {material!r}")
    forbidden = {
        "principal_id", "agent_id", "application_id", "skill_id",
        "approval_id", "admin_operation", "credential_ref", "lease_id", "executor_id",
    }
    if forbidden.intersection(material):
        raise SystemExit("controller authority/admin/credential material crossed fixture boundary")
    print(marker)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("declare")
    q = sub.add_parser("request")
    q.add_argument("--request-id", required=True)
    q.add_argument("--note-id", required=True)
    q.add_argument("--content", required=True)
    q.add_argument("--idempotency-key", required=True)
    q = sub.add_parser("resume")
    q.add_argument("--continuation-id", required=True)
    sub.add_parser("consume-result")
    sub.add_parser("consume-status")
    a = p.parse_args()

    if a.command == "declare":
        print(json.dumps(declaration(), sort_keys=True))
        return
    if a.command == "request":
        print(json.dumps(request(a), sort_keys=True))
        return
    if a.command == "resume":
        expected = json.load(sys.stdin)
        print(json.dumps({
            "schema": RESUME_SCHEMA,
            "continuation_id": a.continuation_id,
            "expected_request": expected,
        }, sort_keys=True))
        return
    if a.command == "consume-result":
        consume(RESULT_SCHEMA, "PI003_NATIVE_FIXTURE_RESULT=PASS")
        return
    if a.command == "consume-status":
        consume(STATUS_SCHEMA, "PI003_NATIVE_FIXTURE_STATUS=PASS")
        return
    raise SystemExit(2)


if __name__ == "__main__":
    main()
