from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from packages.admin import AdminRequest, AdminService
from packages.adapters.pi.production import (
    PI_V1_AGENT_ID, PI_V1_APPLICATION_ID, PI_V1_CAPABILITY_MANIFEST,
    PI_V1_PRINCIPAL_ID, PI_V1_SKILL_ID, PiPermissionRuntime,
)
from packages.capabilities import CapabilityManifest
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.policy import StandingPolicyCondition, StandingPolicyRule
from packages.state import AgentIdentityRepository, ApprovalRepository, EmergencyPauseRepository, SQLiteStateStore

class PiV1PermissionRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="lac-pi001-runtime-")
        self.root=Path(self.tmp.name); self.workspace=self.root/"workspace"; self.workspace.mkdir()
        self.store=SQLiteStateStore(self.root/"controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active(PI_V1_AGENT_ID,PI_V1_PRINCIPAL_ID)
        self.admin=AdminService(self.store,owner_uid=os.getuid())
        self.fs=FilesystemEffectAdapter(self.workspace)
        self.shell=ShellEffectAdapter(self.workspace,allowed_executables=(Path("/usr/bin/printf"),))
        self.runtime=self.make_runtime("run:pi001:test")
        self.register_manifest()
    def tearDown(self):
        self.store.close(); self.tmp.cleanup()
    def make_runtime(self,run_id):
        return PiPermissionRuntime(
            store=self.store,filesystem_adapter=self.fs,shell_adapter=self.shell,run_id=run_id
        )
    def admin_call(self,operation,arguments):
        req=AdminRequest.create(
            request_id=f"admin:pi001:{operation}:{os.urandom(6).hex()}",
            operation=operation,arguments=arguments
        )
        return self.admin.execute(req,peer_uid=os.getuid())
    def register_manifest(self):
        manifest=CapabilityManifest.create(PI_V1_CAPABILITY_MANIFEST)
        return self.admin_call("skills.register",{"manifest":json.loads(manifest.canonical_json())})
    def set_rules(self,rules):
        return self.admin_call("permissions.replace",{
            "rules":[r.to_material() for r in rules],"defaults":[]
        })
    def msg(self,call_id,tool="lac_fs_create",**kwargs):
        if tool=="lac_fs_create":
            args={"path":kwargs.get("path",f"{call_id}.txt"),"content":kwargs.get("content",call_id)}
        elif tool=="lac_fs_read":
            args={"path":kwargs["path"]}
        else: args=kwargs
        return {"toolCallId":call_id,"toolName":tool,"arguments":args}

    def test_registration_zero_authority_unconfigured_is_terminal_then_fresh_request_can_use_policy(self):
        msg=self.msg("unconfigured",path="zero.txt",content="blocked")
        first=self.runtime.submit_message(msg)
        self.assertEqual(first["authority_outcome"],"DENY")
        self.assertTrue(first["permission_configuration"]["required"])
        self.assertEqual(first["permission_configuration"]["reason"],"NO_CONFIGURED_STANDING_PERMISSION")
        self.assertFalse((self.workspace/"zero.txt").exists())
        self.set_rules([StandingPolicyRule.create(
            rule_id="allow-create",application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,action="filesystem.create",decision="ALLOW"
        )])
        still=self.runtime.submit_message(msg)
        self.assertEqual(still["authority_outcome"],"DENY")
        self.assertFalse((self.workspace/"zero.txt").exists())
        fresh=self.runtime.submit_message(self.msg("fresh",path="fresh.txt",content="allowed"))
        self.assertEqual((fresh["authority_outcome"],fresh["execution_state"]),("ALLOW","SUCCEEDED"))
        self.assertEqual((self.workspace/"fresh.txt").read_text(),"allowed")

    def test_configured_deny_has_no_discovery_noise_or_effect(self):
        self.set_rules([StandingPolicyRule.create(
            rule_id="deny-create",application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,action="filesystem.create",decision="DENY"
        )])
        result=self.runtime.submit_message(self.msg("deny",path="denied.txt",content="never"))
        self.assertEqual(result["authority_outcome"],"DENY")
        self.assertFalse(result["permission_configuration"]["required"])
        self.assertFalse((self.workspace/"denied.txt").exists())

    def test_conditional_allow_consumes_trusted_capability_metadata(self):
        (self.workspace/"read.txt").write_text("trusted-read")
        condition=StandingPolicyCondition.create(source="CAPABILITY",key="read_only",equals=True)
        self.set_rules([StandingPolicyRule.create(
            rule_id="allow-read-only",application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,conditions=[condition],decision="ALLOW"
        )])
        read=self.runtime.submit_message(self.msg("read",tool="lac_fs_read",path="read.txt"))
        self.assertEqual((read["authority_outcome"],read["execution_state"]),("ALLOW","SUCCEEDED"))
        write=self.runtime.submit_message(self.msg("write",path="write.txt",content="no"))
        self.assertEqual(write["authority_outcome"],"DENY")
        self.assertTrue(write["permission_configuration"]["required"])
        self.assertFalse((self.workspace/"write.txt").exists())

    def test_exact_approval_mutation_fail_closed_and_duplicate_replays(self):
        self.set_rules([StandingPolicyRule.create(
            rule_id="ask-create",application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,action="filesystem.create",decision="REQUIRE_APPROVAL"
        )])
        msg=self.msg("approval",path="approval.txt",content="approved")
        pending=self.runtime.submit_message(msg)
        self.assertEqual((pending["authority_outcome"],pending["execution_state"]),
                         ("REQUIRE_APPROVAL","PENDING_APPROVAL"))
        approved=self.admin_call("approvals.approve",{"decision_id":pending["decision_id"]})
        approval_id=approved["approval"]["approval_id"]
        self.assertFalse((self.workspace/"approval.txt").exists())
        with self.assertRaises(Exception):
            self.runtime.submit_message(self.msg("approval",path="approval.txt",content="mutated"))
        self.assertIsNone(ApprovalRepository(self.store).get(approval_id).consumed_at)
        executed=self.runtime.submit_message(msg)
        self.assertEqual((executed["authority_outcome"],executed["execution_state"]),("ALLOW","SUCCEEDED"))
        self.assertEqual((self.workspace/"approval.txt").read_text(),"approved")
        self.assertIsNotNone(ApprovalRepository(self.store).get(approval_id).consumed_at)
        replay=self.runtime.submit_message(msg)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"]["receipt_id"],executed["receipt"]["receipt_id"])

    def test_restart_preserves_pending_closure_and_terminal_receipt(self):
        blocked_msg=self.msg("pending",path="pending.txt",content="blocked")
        blocked=self.runtime.submit_message(blocked_msg)
        pending_id=blocked["permission_configuration"]["pending_id"]
        self.set_rules([StandingPolicyRule.create(
            rule_id="allow-create-restart",application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,action="filesystem.create",decision="ALLOW"
        )])
        success_msg=self.msg("success",path="success.txt",content="once")
        success=self.runtime.submit_message(success_msg)
        restarted=self.make_runtime("run:pi001:test")
        again=restarted.submit_message(blocked_msg)
        self.assertEqual(again["permission_configuration"]["pending_id"],pending_id)
        replay=restarted.submit_message(success_msg)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"]["receipt_id"],success["receipt"]["receipt_id"])

    def test_unknown_new_capability_still_uses_p002_quarantine(self):
        material={
            "schema":"lac.external-consumer-request/v1","request_id":"effect:pi001:unknown",
            "run_id":"run:pi001:test","action":"filesystem.future-action",
            "resource":"filesystem:workspace","arguments":{"path":"future.txt"},
            "idempotency_key":"idem:pi001:unknown",
        }
        result=self.runtime._decorate(self.runtime.runtime.submit(material))
        self.assertEqual(result["authority_outcome"],"DENY")
        self.assertTrue(result["permission_configuration"]["required"])
        self.assertEqual(result["permission_configuration"]["reason"],"UNKNOWN_ACTION")
        self.assertFalse((self.workspace/"future.txt").exists())

    def test_external_runtime_binding_and_admin_separation_remain_phase4_owned(self):
        self.assertEqual(self.runtime.runtime.application_id,PI_V1_APPLICATION_ID)
        self.assertEqual(self.runtime.runtime.skill_id,PI_V1_SKILL_ID)
        for name in ("approve","register","replace_policy","admin"):
            self.assertFalse(hasattr(self.runtime.runtime,name))

if __name__=="__main__": unittest.main(verbosity=2)
