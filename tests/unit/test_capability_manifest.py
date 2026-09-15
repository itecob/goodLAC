import copy
import json
import unittest

from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityManifest,
    CapabilityManifestError,
    DuplicateManifestKey,
    UnsupportedCapabilityManifestVersion,
)


def manifest_fixture():
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "workspace-skill",
        "actions": [
            {
                "action": "filesystem.read",
                "resource": {
                    "type": "filesystem.workspace",
                    "selectors": ["filesystem:workspace"],
                },
                "arguments": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1, "maxLength": 512}
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                "security_properties": ["read_only"],
            },
            {
                "action": "filesystem.replace",
                "resource": {
                    "type": "filesystem.workspace",
                    "selectors": ["filesystem:workspace"],
                },
                "arguments": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1, "maxLength": 512},
                        "content": {"type": "string", "maxLength": 65536},
                    },
                    "required": ["content", "path"],
                    "additionalProperties": False,
                },
                "security_properties": ["local_mutation"],
            },
        ],
        "display": {"name": "Workspace skill", "description": "Synthetic fixture"},
    }


class CapabilityManifestTests(unittest.TestCase):
    def test_canonical_manifest_normalizes_set_like_ordering(self):
        first = manifest_fixture()
        second = copy.deepcopy(first)
        second["actions"].reverse()
        second["actions"][0]["security_properties"] = list(
            reversed(second["actions"][0]["security_properties"])
        )
        a = CapabilityManifest.create(first)
        b = CapabilityManifest.create(second)
        self.assertEqual(a.canonical_hash, b.canonical_hash)
        self.assertEqual(a.security_hash, b.security_hash)
        self.assertEqual(a.canonical_json(), b.canonical_json())
        self.assertEqual([item["action"] for item in a.actions], ["filesystem.read", "filesystem.replace"])

    def test_display_metadata_does_not_change_security_hash(self):
        original = CapabilityManifest.create(manifest_fixture())
        changed = manifest_fixture()
        changed["display"]["description"] = "Different non-authority description"
        revised = CapabilityManifest.create(changed)
        self.assertNotEqual(original.canonical_hash, revised.canonical_hash)
        self.assertEqual(original.security_hash, revised.security_hash)

    def test_unknown_top_level_field_fails_closed(self):
        value = manifest_fixture()
        value["permission"] = "ALLOW"
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_unsupported_version_fails_closed(self):
        value = manifest_fixture()
        value["manifest_version"] = 2
        with self.assertRaises(UnsupportedCapabilityManifestVersion):
            CapabilityManifest.create(value)

    def test_duplicate_action_identity_fails_closed(self):
        value = manifest_fixture()
        value["actions"].append(copy.deepcopy(value["actions"][0]))
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_duplicate_selector_fails_closed(self):
        value = manifest_fixture()
        value["actions"][0]["resource"]["selectors"] = [
            "filesystem:workspace",
            "filesystem:workspace",
        ]
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_wildcard_selector_is_ambiguous_and_fails_closed(self):
        value = manifest_fixture()
        value["actions"][0]["resource"]["selectors"] = ["filesystem:*" ]
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_unsupported_security_property_fails_closed(self):
        value = manifest_fixture()
        value["actions"][0]["security_properties"] = ["model_says_safe"]
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_unbounded_string_schema_fails_closed(self):
        value = manifest_fixture()
        del value["actions"][0]["arguments"]["properties"]["path"]["maxLength"]
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_object_arguments_must_reject_additional_properties(self):
        value = manifest_fixture()
        value["actions"][0]["arguments"]["additionalProperties"] = True
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_unknown_argument_schema_keyword_fails_closed(self):
        value = manifest_fixture()
        value["actions"][0]["arguments"]["properties"]["path"]["default"] = "/tmp/secret"
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_boolean_manifest_version_is_not_version_one(self):
        value = manifest_fixture()
        value["manifest_version"] = True
        with self.assertRaises(UnsupportedCapabilityManifestVersion):
            CapabilityManifest.create(value)

    def test_non_string_required_entry_fails_closed(self):
        value = manifest_fixture()
        value["actions"][0]["arguments"]["required"] = [{"path": True}]
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_non_string_security_property_fails_closed(self):
        value = manifest_fixture()
        value["actions"][0]["security_properties"] = [{"unsafe": True}]
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(value)

    def test_duplicate_raw_json_identity_key_fails_closed(self):
        raw = (
            '{"schema":"lac.capability-manifest/v1","manifest_version":1,'
            '"application_id":"one","application_id":"two","skill_id":"skill",'
            '"actions":[]}'
        )
        with self.assertRaises(DuplicateManifestKey):
            CapabilityManifest.from_json(raw)

    def test_persisted_json_must_be_exactly_canonical(self):
        manifest = CapabilityManifest.create(manifest_fixture())
        pretty = json.dumps(manifest.canonical_material(), indent=2, sort_keys=True)
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.from_json(pretty, require_canonical=True)
        round_trip = CapabilityManifest.from_json(manifest.canonical_json(), require_canonical=True)
        self.assertEqual(round_trip.canonical_hash, manifest.canonical_hash)


if __name__ == "__main__":
    unittest.main()
