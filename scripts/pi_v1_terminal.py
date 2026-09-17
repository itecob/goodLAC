#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, selectors, signal, subprocess, sys, time, uuid
from pathlib import Path
from typing import Any, Mapping
REPO_ROOT=Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0,str(REPO_ROOT))
import scripts.a004_terminal as baseline
from packages.adapters.pi.production import PI_V1_APPLICATION_ID, PI_V1_SKILL_ID
from packages.lacctl import LacctlClient
from packages.policy import StandingPolicyRule

EFFECT_BRIDGE=REPO_ROOT/"scripts"/"pi_v1_controller_bridge.py"
ADMIN_SERVER=REPO_ROOT/"scripts"/"pi_v1_admin_server.py"
APPROVAL_WAIT_LIMIT_SECONDS=3600

class PiV1TerminalError(RuntimeError): pass
def default_workspace(): return Path.home()/".local/share/local-agent-controller/pi-v1-workspace"
def default_state(): return Path.home()/".local/state/local-agent-controller/pi-v1/controller.db"
def default_trace(): return Path.home()/".local/state/local-agent-controller/pi-v1/effect-trace.jsonl"

def system_prompt():
    return "\n".join((
        "You are running inside the explicit Local Agent Controller governed Pi v1 profile.",
        "You have exactly four consequential-effect tools: lac_fs_read, lac_fs_create, lac_fs_replace, lac_shell_exec.",
        "Every effect is submitted to LAC capability validation, standing permission, exact approval when required, dispatch, sandboxing and durable receipts.",
        "A permission-configuration denial is terminal for that exact request; after the owner changes standing permission, issue a fresh tool request.",
        "For REQUIRE_APPROVAL the trusted host keeps the exact current request pending while the owner decides through lacctl.",
        "All filesystem paths are relative to the governed workspace.",
        "For lac_shell_exec argv excludes argv[0]; the initial profile accepts an empty environment object only.",
        "Do not claim success unless execution_state is SUCCEEDED. Do not expose hidden reasoning or credentials.",
    ))

def bridge_json(state,workspace,run_id,payload):
    proc=subprocess.run(
        [sys.executable,str(EFFECT_BRIDGE),"effect","--state",str(state),"--workspace",str(workspace),"--run-id",run_id],
        input=json.dumps(dict(payload)),text=True,capture_output=True,cwd=REPO_ROOT,timeout=90,check=False
    )
    if proc.returncode: raise PiV1TerminalError(f"effect bridge exited {proc.returncode}: {proc.stderr[-1200:]}")
    try: value=json.loads(proc.stdout)
    except json.JSONDecodeError as exc: raise PiV1TerminalError("effect bridge emitted malformed JSON") from exc
    if not isinstance(value,dict): raise PiV1TerminalError("effect bridge result must be an object")
    return value

def initialize_state(state,workspace):
    workspace.mkdir(parents=True,exist_ok=True); workspace.chmod(0o700)
    proc=subprocess.run(
        [sys.executable,str(EFFECT_BRIDGE),"init","--state",str(state),"--workspace",str(workspace)],
        cwd=REPO_ROOT,text=True,capture_output=True,timeout=30,check=False
    )
    if proc.returncode: raise PiV1TerminalError(f"state initialization failed: {proc.stdout}{proc.stderr}")

def start_admin_server(state):
    proc=subprocess.Popen(
        [sys.executable,"-u",str(ADMIN_SERVER),"--state",str(state),"--parent-pid",str(os.getpid())],
        cwd=REPO_ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,bufsize=1
    )
    assert proc.stdout is not None
    sel=selectors.DefaultSelector(); sel.register(proc.stdout,selectors.EVENT_READ)
    try:
        ready=sel.select(timeout=8)
        if not ready:
            stderr=proc.stderr.read()[-1600:] if proc.poll() is not None and proc.stderr else ""
            proc.kill(); raise PiV1TerminalError(f"admin server did not become ready: {stderr}")
        line=proc.stdout.readline()
    finally: sel.close()
    if not line: raise PiV1TerminalError("admin server exited before ready")
    try: value=json.loads(line)
    except json.JSONDecodeError as exc: raise PiV1TerminalError("admin ready message malformed") from exc
    if value.get("schema")!="lac.pi-v1-admin-ready/v1":
        raise PiV1TerminalError(f"unexpected admin ready message: {value!r}")
    return proc

def stop_admin_server(proc):
    if proc is None: return
    if proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=5)

def effect_line(result):
    receipt=result.get("receipt")
    rid=receipt.get("receipt_id") if isinstance(receipt,Mapping) else "-"
    return (
        f"[effect] authority={result.get('authority_outcome','?')} "
        f"state={result.get('execution_state','?')} request={result.get('request_id','-')} receipt={rid or '-'}"
    )

class PiV1InteractiveSession(baseline.InteractiveSession):
    def __init__(self,*,workspace,state,trace):
        super().__init__(workspace=workspace,state=state,trace=trace,system_prompt=system_prompt())
        self.run_id=f"run:pi-v1:{uuid.uuid4().hex}"

    def _trace_result(self,payload,result):
        self.trace.parent.mkdir(parents=True,exist_ok=True)
        with self.trace.open("a",encoding="utf-8") as f:
            f.write(json.dumps({
                "toolCallId":payload.get("toolCallId"),"toolName":payload.get("toolName"),
                "request_id":result.get("request_id"),"authority_outcome":result.get("authority_outcome"),
                "execution_state":result.get("execution_state"),"decision_id":result.get("decision_id"),
                "permission_configuration":result.get("permission_configuration"),
                "receipt_id":result.get("receipt",{}).get("receipt_id") if isinstance(result.get("receipt"),Mapping) else None,
            },sort_keys=True)+"\n")

    def _effect(self,payload):
        if not isinstance(payload,Mapping): baseline.fail("effect_request payload must be an object")
        print(f"[tool] {baseline.tool_summary(payload)}",flush=True)
        started=time.monotonic(); announced=False
        while True:
            response=bridge_json(self.state,self.workspace,self.run_id,payload)
            if response.get("ok") is not True: return response
            result=response.get("result")
            if not isinstance(result,Mapping): raise PiV1TerminalError("effect result malformed")
            result=dict(result); print(effect_line(result),flush=True)
            permission=result.get("permission_configuration")
            if isinstance(permission,Mapping) and permission.get("required") is True:
                print(
                    f"[permission] configuration required; pending={permission.get('pending_id')} "
                    f"reason={permission.get('reason')}. Exact effect is closed; configure future permission "
                    "with lacctl, then issue a fresh request.",flush=True
                )
                self._trace_result(payload,result); return response
            if result.get("authority_outcome")=="REQUIRE_APPROVAL" and result.get("execution_state")=="PENDING_APPROVAL":
                decision=result.get("decision_id")
                if not announced:
                    print(
                        f"[approval] exact owner decision required; decision={decision}. In another terminal: "
                        f"scripts/lacctl approvals approve {decision} (or reject it). "
                        "The broker retries this same canonical request.",flush=True
                    ); announced=True
                if time.monotonic()-started>=APPROVAL_WAIT_LIMIT_SECONDS:
                    self._trace_result(payload,result); return response
                time.sleep(1.0); continue
            self._trace_result(payload,result); return response

    def tool_probe(self,*,tool_call_id,tool_name,arguments):
        probe_id="probe-"+uuid.uuid4().hex
        self._write({
            "type":"tool_probe","id":probe_id,"toolCallId":tool_call_id,
            "toolName":tool_name,"arguments":dict(arguments)
        })
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            message=self._read(min(30,max(0.1,deadline-time.monotonic())))
            if message.get("type")=="rpc":
                if message.get("kind")!="effect_request":
                    baseline.fail("tool probe requested unexpected host capability")
                handled=self._effect(message.get("payload"))
                self._write({"type":"rpc_response","id":message.get("id"),"ok":True,"payload":handled})
                continue
            if message.get("type")=="tool_probe_result":
                if message.get("id")!=probe_id: baseline.fail("tool probe result did not bind active probe")
                details=message.get("details")
                if not isinstance(details,Mapping): baseline.fail("tool probe lacks bounded details")
                return dict(details)
            baseline.fail(f"unexpected Pi message during tool probe: {message!r}")
        baseline.fail("tool probe timed out")

def profile_status(session,runtime_mode):
    return (
        f"runtime={runtime_mode} model={baseline.SERVED_MODEL_ID} pi_agent_core=0.85.1\n"
        f"pi_pid={session.pi_pid or '-'} profile=lac-governed-v1 sandbox=bubblewrap network=none\n"
        f"tools={','.join(baseline.EXPECTED_TOOLS)}\n"
        f"application={PI_V1_APPLICATION_ID} skill={PI_V1_SKILL_ID}\n"
        f"workspace={session.workspace}\nstate={session.state}\ntrace={session.trace}\n"
        "standalone_pi=separate_and_not_claimed_as_lac_governed"
    )

def run_profile_probe(workspace,state,trace):
    denied=workspace/"pi001-denied-must-not-exist.txt"
    allowed=workspace/"pi001-allowed.txt"
    denied.unlink(missing_ok=True); allowed.unlink(missing_ok=True)
    with PiV1InteractiveSession(workspace=workspace,state=state,trace=trace) as session:
        r=session.tool_probe(
            tool_call_id="pi001-profile-denied",tool_name="lac_fs_create",
            arguments={"path":denied.name,"content":"must-not-execute"}
        )
        if r.get("authority_outcome")!="DENY": raise PiV1TerminalError(f"unconfigured request did not DENY: {r!r}")
        pc=r.get("permission_configuration")
        if not isinstance(pc,Mapping) or pc.get("required") is not True:
            raise PiV1TerminalError("unconfigured request did not create permission work")
        if denied.exists(): raise PiV1TerminalError("unconfigured request produced host effect")
        rule=StandingPolicyRule.create(
            rule_id="pi001-profile-probe-allow-create",
            application_id=PI_V1_APPLICATION_ID,skill_id=PI_V1_SKILL_ID,
            action="filesystem.create",resource_selector="filesystem:workspace",decision="ALLOW"
        )
        LacctlClient().call("permissions.replace",{"rules":[rule.to_material()],"defaults":[]})
        r=session.tool_probe(
            tool_call_id="pi001-profile-allowed",tool_name="lac_fs_create",
            arguments={"path":allowed.name,"content":"pi001-real-pi-path"}
        )
        if r.get("authority_outcome")!="ALLOW" or r.get("execution_state")!="SUCCEEDED":
            raise PiV1TerminalError(f"configured request failed: {r!r}")
        if allowed.read_text(encoding="utf-8")!="pi001-real-pi-path":
            raise PiV1TerminalError("unexpected filesystem content")
        replay=session.tool_probe(
            tool_call_id="pi001-profile-allowed",tool_name="lac_fs_create",
            arguments={"path":allowed.name,"content":"pi001-real-pi-path"}
        )
        if replay.get("replayed") is not True:
            raise PiV1TerminalError("duplicate did not replay terminal receipt")
        print(profile_status(session,"profile-probe"))
        print("LAC_PI001_REAL_PI_PERMISSION_PATH=PASS")
        print("LAC_PI001_REAL_PI_DUPLICATE_PREVENTION=PASS")
    print("LAC_PI001_PROFILE_PROBE=PASS"); return 0

def run_interactive(workspace,state,trace,runtime_mode):
    with PiV1InteractiveSession(workspace=workspace,state=state,trace=trace) as session:
        print("LAC-governed Pi v1 profile. Type /help for controls.")
        print(profile_status(session,runtime_mode))
        while True:
            try: raw=baseline.read_terminal_input("\nlac-pi> ")
            except EOFError: raw="/quit"
            try: raw=baseline.validate_terminal_input(raw)
            except baseline.A004InputRejected as exc:
                print(f"input> rejected: {exc}"); continue
            cmd=raw.strip()
            if cmd in {"/quit","quit","exit"}: break
            if cmd in {"/help","help"}:
                print("/help show controls\n/status show governed profile status\n/quit clean shutdown\n"
                      "Other text is sent to pinned Pi. Use scripts/lacctl in another owner terminal for admin.")
                continue
            if cmd in {"/status","status"}: print(profile_status(session,runtime_mode)); continue
            if not cmd: continue
            print(f"assistant> {session.prompt(raw)}")
    print("LAC_PI_V1_TERMINAL_SHUTDOWN=CLEAN"); return 0

def main():
    p=argparse.ArgumentParser(description="Production LAC-governed Pi v1 profile")
    p.add_argument("--workspace",type=Path,default=default_workspace())
    p.add_argument("--state",type=Path,default=default_state())
    p.add_argument("--trace",type=Path,default=default_trace())
    p.add_argument("--runtime",choices=("manage","external"),default="manage")
    p.add_argument("--profile-probe",action="store_true")
    a=p.parse_args()
    baseline.verify_accepted_pins()
    workspace=a.workspace.expanduser().resolve()
    state=a.state.expanduser().resolve()
    trace=a.trace.expanduser().resolve()
    initialize_state(state,workspace)
    admin=None; runtime=None
    old=signal.getsignal(signal.SIGTERM)
    def terminate(_s,_f): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,terminate)
    try:
        admin=start_admin_server(state)
        if a.profile_probe: return run_profile_probe(workspace,state,trace)
        mode="external"
        if a.runtime=="manage":
            runtime=baseline.FreeTokenRuntime(); mode=runtime.ensure()
        else:
            exact,detail=baseline.probe_exact_endpoint(baseline.runtime_assets())
            if not exact: raise PiV1TerminalError(f"external FreeToken endpoint is not exact accepted runtime: {detail}")
        return run_interactive(workspace,state,trace,mode)
    finally:
        signal.signal(signal.SIGTERM,old)
        if runtime is not None: runtime.stop()
        stop_admin_server(admin)

if __name__=="__main__":
    try: raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nLAC_PI_V1_TERMINAL_SHUTDOWN=INTERRUPTED_CLEAN"); raise SystemExit(130)
    except (PiV1TerminalError,baseline.A004TerminalError) as exc:
        print(f"LAC_PI_V1_TERMINAL=FAIL: {exc}",file=sys.stderr); raise SystemExit(1)
