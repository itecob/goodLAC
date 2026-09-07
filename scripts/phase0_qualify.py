#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_FILE = ROOT / 'qualification' / 'candidates.json'
EVIDENCE_DIR = ROOT / 'qualification' / 'evidence'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache'))) / 'local-agent-controller' / 'phase0' / 'upstream'
CI_ENV = {**os.environ, 'CI':'1', 'NO_COLOR':'1', 'NPM_CONFIG_FUND':'false', 'NPM_CONFIG_AUDIT':'false'}
QUALIFICATION_NODE_VERSION = '22.23.2'
MISE = shutil.which('mise') or (str(Path.home()/'.local/bin/mise') if (Path.home()/'.local/bin/mise').is_file() else None)

EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

class GateError(RuntimeError): pass

def now(): return datetime.now(timezone.utc).isoformat()
def sha256_file(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def node_tool_cmd(*cmd: str):
    if not MISE:
        raise GateError('mise is required for the pinned Node qualification runtime')
    return [MISE, 'exec', f'node@{QUALIFICATION_NODE_VERSION}', '--', *cmd]

def run(cmd, cwd=None, timeout=900, check=True):
    start=time.time()
    p=subprocess.run(cmd, cwd=cwd, env=CI_ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    rec={'command':cmd,'cwd':str(cwd) if cwd else None,'rc':p.returncode,'seconds':round(time.time()-start,3),'output':p.stdout[-20000:]}
    if check and p.returncode!=0: raise GateError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout[-4000:]}")
    return rec

def clone_exact(item):
    dest=CACHE/item['key']
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True)
    run(['git','init','-q'], dest)
    run(['git','remote','add','origin','https://github.com/'+item['repo']+'.git'], dest)
    try:
        run(['git','fetch','--depth=1','origin',item['sha']], dest, timeout=1200)
    except Exception:
        # GitHub normally permits SHA fetches; fall back to fetching remote heads/tags without accepting a moving ref.
        run(['git','fetch','--depth=50','origin','+refs/heads/*:refs/remotes/origin/*','+refs/tags/*:refs/tags/*'], dest, timeout=1200)
        run(['git','cat-file','-e',item['sha']+'^{commit}'], dest)
    run(['git','checkout','-q','--detach',item['sha']], dest)
    actual=run(['git','rev-parse','HEAD'], dest)['output'].strip()
    if actual != item['sha']: raise GateError(f"{item['key']}: pinned SHA mismatch {actual}")
    return dest

def detect_license(dest: Path):
    roots=[]
    for name in ['LICENSE','LICENSE.md','LICENSE.txt','COPYING','COPYING.md']:
        p=dest/name
        if p.is_file(): roots.append(p)
    if not roots: return {'family':'UNRESOLVED','file':None,'sha256':None,'first_line':None}
    p=roots[0]; txt=p.read_text(errors='replace')
    low=txt.lower()
    if 'mit license' in low and 'permission is hereby granted' in low: fam='MIT'
    elif 'apache license' in low and 'version 2.0' in low: fam='Apache-2.0'
    else: fam='OTHER'
    return {'family':fam,'file':p.name,'sha256':sha256_file(p),'first_line':txt.splitlines()[0] if txt.splitlines() else ''}

def observed_version(dest: Path):
    p=dest/'package.json'
    if p.is_file():
        try:
            v=json.loads(p.read_text()).get('version')
            if isinstance(v,str): return v
        except Exception: pass
    p=dest/'pyproject.toml'
    if p.is_file():
        m=re.search(r'(?m)^version\s*=\s*[\"\']([^\"\']+)', p.read_text(errors='replace'))
        if m: return m.group(1)
    p=dest/'Cargo.toml'
    if p.is_file():
        m=re.search(r'(?m)^version\s*=\s*[\"\']([^\"\']+)', p.read_text(errors='replace'))
        if m: return m.group(1)
    p=dest/'python/freetoken/version.py'
    if p.is_file():
        m=re.search(r'(?m)^__version__\s*=\s*[\"\']([^\"\']+)', p.read_text(errors='replace'))
        if m: return m.group(1)
    return None

def build_metadata(dest: Path):
    manifests=[]
    for rel in ['package.json','package-lock.json','pnpm-lock.yaml','yarn.lock','pyproject.toml','requirements.txt','Cargo.toml','Cargo.lock','go.mod','go.sum','docker-compose.yml','docker-compose.yaml','compose.yml','compose.yaml','Makefile']:
        if (dest/rel).is_file(): manifests.append(rel)
    out={'manifests':manifests,'runtime_requirements':{},'declared_dependency_count':None}
    p=dest/'package.json'
    if p.is_file():
        try:
            d=json.loads(p.read_text())
            out['runtime_requirements']['node']=(d.get('engines') or {}).get('node')
            deps={**(d.get('dependencies') or {}),**(d.get('optionalDependencies') or {})}
            out['declared_dependency_count']=len(deps)
        except Exception: pass
    p=dest/'pyproject.toml'
    if p.is_file():
        txt=p.read_text(errors='replace')
        m=re.search(r'(?m)^requires-python\s*=\s*["\']([^"\']+)',txt)
        if m: out['runtime_requirements']['python']=m.group(1)
        if out['declared_dependency_count'] is None:
            block=re.search(r'(?ms)^dependencies\s*=\s*\[(.*?)\]\s*$',txt)
            if block: out['declared_dependency_count']=len(re.findall(r'(?m)^\s*["\']',block.group(1)))
    p=dest/'Cargo.toml'
    if p.is_file():
        txt=p.read_text(errors='replace')
        m=re.search(r'(?m)^rust-version\s*=\s*["\']([^"\']+)',txt)
        if m: out['runtime_requirements']['rust']=m.group(1)
    p=dest/'go.mod'
    if p.is_file():
        txt=p.read_text(errors='replace')
        m=re.search(r'(?m)^go\s+([^\s]+)',txt)
        if m: out['runtime_requirements']['go']=m.group(1)
    out['runtime_requirements']={k:v for k,v in out['runtime_requirements'].items() if v}
    return out

def lightweight_source_test(key: str, dest: Path):
    # For deferred/reference components, Phase 0 does not install their full runtime stacks.
    # These checks validate parseable source/package surfaces relevant to the disposition.
    if key=='pi':
        need(MISE is not None,'mise is required for Pi source/package qualification')
        pkg=json.loads(text(dest,'package.json'))
        need((pkg.get('engines') or {}).get('node') is not None,'Pi Node engine declaration missing')
        nodev=run(node_tool_cmd('node','--version'))['output'].strip()
        need(nodev == 'v'+QUALIFICATION_NODE_VERSION,f'Pi qualification Node mismatch: {nodev}')
        rec=run(node_tool_cmd('node','--check','scripts/check-pinned-deps.mjs'),dest,timeout=120)
        return {'kind':'SOURCE_PACKAGE_CHECK','status':'PASS','qualification_node':nodev,'command':rec}
    if key=='freetoken':
        rec=run([sys.executable,'-m','compileall','-q','python/freetoken'],dest,timeout=180)
        pyproject=text(dest,'pyproject.toml')
        need('OpenAI-' in pyproject or 'OpenAI' in pyproject,'FreeToken API compatibility metadata not found')
        return {'kind':'SOURCE_COMPILE_CHECK','status':'PASS','command':rec,'note':'GPU/runtime pytest suite deferred to Phase 3; Phase 0 does not install the CUDA inference stack.'}
    return {'kind':'SOURCE_PROBE','status':'PASS','note':'Component is reference/deferred in the active phase; no runtime dependency stack is introduced by Phase 0.'}

def stable_tag(repo: str):
    try:
        out=run(['git','ls-remote','--tags','--refs','https://github.com/'+repo+'.git'], timeout=120)['output']
    except Exception: return None
    tags=[line.split('\t',1)[1].removeprefix('refs/tags/') for line in out.splitlines() if '\t' in line]
    preferred=[]
    for t in tags:
        m=re.search(r'(?<!\d)(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$', t)
        if m:
            nums=tuple(map(int,m.groups()))
            # Prefer canonical vX.Y.Z or X.Y.Z tags over component-specific tags.
            canonical=2 if re.fullmatch(r'v?\d+\.\d+\.\d+(?:[-+].*)?', t) else 1
            prerelease=0 if '-' not in t.split('/')[-1] else -1
            preferred.append((canonical, prerelease, nums, t))
    return max(preferred)[3] if preferred else None

def need(cond, msg):
    if not cond: raise GateError(msg)

def text(dest, rel):
    p=dest/rel
    need(p.is_file(), f"missing required file {rel}")
    return p.read_text(errors='replace')

def probe_airlock(dest):
    gate=text(dest,'src/middleware/core/hitl-gate.ts')
    chain=text(dest,'src/middleware/chain-builder.ts')
    eng=text(dest,'src/hitl/engine.ts')
    execute=text(dest,'src/middleware/core/execute.ts')
    pkg=json.loads(text(dest,'package.json'))
    need(pkg.get('version')=='0.2.38','Airlock pinned package version changed unexpectedly')
    need('const approvalArgs = redactApprovalArgs(auditLogger, ctx.args);' in gate,'Airlock approval redaction path not found')
    need('const ticket = hitlEngine.create' in gate,'Airlock HITL ticket creation not found')
    need("result === 'denied'" in gate and "result === 'timeout'" in gate,'Airlock deny/timeout branches not found')
    need('return next();' in gate,'Airlock approved path no longer continues to next middleware')
    need(chain.find('allowlistMiddleware()') < chain.find('hitlGateMiddleware()') < chain.find('executeMiddleware()'),'Airlock middleware order probe failed')
    after_wait=gate[gate.find('result = await ticket.result;'):]
    need('allowlist.evaluate' not in after_wait,'Airlock now appears to re-evaluate allowlist after HITL; ADR must be re-reviewed')
    need('canonical' not in gate.lower() and 'sha256' not in gate.lower(),'Airlock HITL gate now appears to include canonical/hash binding; ADR must be re-reviewed')
    need('insertHitl' in eng and 'recoverPending' in eng and 'updateHitlStatus' in eng,'Airlock durable HITL lifecycle probes failed')
    need('this.pending.delete' in eng and 'timeout' in eng,'Airlock one-use/timeout implementation probes failed')
    need("result: 'dispatched'" in execute and 'registry.call(ctx.toolName, ctx.args' in execute and "result: 'success'" in execute,'Airlock execution/audit trace probe failed')
    return {'status':'PASS','finding':'Stock HITL path lacks LAC canonical exact-binding and immediate pre-dispatch policy recheck; AIRLOCK_WRAPPED remains required.','capability_assessment':{'exact_request_approval_binding':'NO_LAC_CANONICAL_BINDING','one_use_approval':'YES_PENDING_TICKET_CONSUMED','approval_expiry':'YES_TIMEOUT','pre_dispatch_policy_recheck':'NO','durable_state':'PARTIAL_PENDING_HITL_RECOVERY','idempotency':'NOT_DEMONSTRATED_AS_LAC_EFFECT_IDEMPOTENCY','emergency_pause':'NOT_DEMONSTRATED','credential_isolation':'NOT_A_LAC_CREDENTIAL_BOUNDARY','sandbox_enforcement':'PRESENT_IN_AIRLOCK_PIPELINE_REQUIRES_PHASE2_HOST_BOUNDARY_QUALIFICATION','crash_restart':'PENDING_APPROVAL_RECOVERY_PRESENT_EXECUTION_RECONCILIATION_NOT_LAC_CANONICAL','audit':'DISPATCH_SUCCESS_ERROR_ROWS_PRESENT'}}

def test_airlock(dest):
    need(MISE is not None,'mise is required to run targeted Airlock upstream tests under the pinned qualification runtime')
    nodev=run(node_tool_cmd('node','--version'))
    need(nodev['output'].strip() == 'v'+QUALIFICATION_NODE_VERSION,f"Airlock qualification Node mismatch: {nodev['output'].strip()}")
    npmv=run(node_tool_cmd('npm','--version'))
    install=run(node_tool_cmd('npm','ci','--no-audit','--no-fund'), dest, timeout=1800)
    typecheck=run(node_tool_cmd('npm','run','typecheck'), dest, timeout=900)
    tests=run(node_tool_cmd('npx','--no-install','vitest','run','test/hitl.test.ts','test/middleware/core-middlewares.test.ts','test/agent-server.test.ts','--maxWorkers=2','--minWorkers=1'), dest, timeout=1200)
    return {'status':'PASS','node':nodev['output'].strip(),'npm':npmv['output'].strip(),'qualification_runtime':'mise node@'+QUALIFICATION_NODE_VERSION,'npm_ci':install,'typecheck':typecheck,'targeted_tests':tests}

def probe_secondary(key,dest):
    r=text(dest,'README.md') if (dest/'README.md').is_file() else ''
    if key=='preloop':
        need('control plane' in r.lower() or 'mcp firewall' in r.lower(),'Preloop control-plane README probe failed')
    elif key=='agentgateway':
        need('mcp' in r.lower(),'agentgateway MCP probe failed')
    elif key=='stonefold':
        need('deterministic' in r.lower() and ('proof-of-concept' in r.lower() or 'proof of concept' in r.lower()),'Stonefold deterministic/POC probe failed')
    elif key=='waggle':
        # Lack of a root license keeps reuse disabled. A newly discovered root license is not auto-authority to copy code; it requires requalification.
        pass
    elif key=='openclaw':
        bind=text(dest,'src/infra/system-run-approval-binding.ts')
        tst=text(dest,'src/infra/system-run-approval-binding.test.ts')
        need('APPROVAL_REQUEST_MISMATCH' in tst and 'argv mismatch' in tst,'OpenClaw exact-binding mismatch tests not found')
        need('approval' in bind.lower() and 'executable' in bind.lower(),'OpenClaw approval binding implementation probe failed')
    elif key=='pi':
        tools=text(dest,'packages/coding-agent/src/core/tools/index.ts')
        need('createReadTool' in tools and 'createWriteTool' in tools and 'AgentTool' in tools,'Pi modular tool factories probe failed')
    elif key=='freetoken':
        need('openai' in r.lower() and ('compatible' in r.lower() or 'api' in r.lower()),'FreeToken OpenAI-compatible endpoint probe failed')
    elif key=='cedar':
        need('authorization' in r.lower() and 'policy' in r.lower(),'Cedar authorization probe failed')
    elif key=='opa':
        need('policy' in r.lower(),'OPA policy-engine probe failed')
    return {'status':'PASS'}

def write_state(status, blockers, nonblocking):
    if status=='PASS':
        state={
          'schema':'lac.project-state/v1','project_version':'0.1.0-dev','phase':'PHASE_0_UPSTREAM_QUALIFICATION',
          'phase_status':'CANDIDATE_FOR_INDEPENDENT_REVIEW','active_task':'LAC-P0-REVIEW','last_accepted_release':None,
          'blockers':[],'nonblocking_findings':nonblocking,
          'next_action':'Run one fresh independent Phase 0 review; on PASS advance to PHASE_1_CONTROLLER_WALKING_SKELETON / LAC-C001.'
        }
        active="""# Active Task\n\n**Task ID:** LAC-P0-REVIEW\n\n**Objective:** Fresh independent read-only review of the Phase 0 upstream qualification candidate against the controlling specification and invariants.\n\n**In scope:** pinned revision/license evidence, Airlock trace and ADR-001, secondary dispositions, deterministic Phase 0 evidence, package/install reproducibility.\n\n**Out of scope:** implementation mutation; Phase 1 code; redesign; future-phase features.\n\n**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `tasks/ACTIVE_TASK.md`, then Phase 0 qualification/ADR/evidence files as required.\n\n**Required outputs:** `PASS` or `BLOCKED`, with findings classified only as `BLOCKER` or `NONBLOCKING`.\n\n**Acceptance tests:** identify a concrete violated invariant/acceptance criterion/security boundary/required functionality/package/data-integrity/license requirement for any BLOCKER.\n\n**Package required?** no\n\n**Next task on success:** `LAC-C001` in Phase 1.\n"""
    else:
        state={
          'schema':'lac.project-state/v1','project_version':'0.1.0-dev','phase':'PHASE_0_UPSTREAM_QUALIFICATION',
          'phase_status':'BLOCKED','active_task':'LAC-Q001-Q004','last_accepted_release':None,
          'blockers':blockers,'nonblocking_findings':nonblocking,
          'next_action':'Return the complete bootstrap qualification output to the Lead Implementation Engineer and remediate only the recorded blocker(s).'
        }
        active="""# Active Task\n\n**Task ID:** LAC-Q001-Q004\n\n**Objective:** Remediate only the recorded Phase 0 qualification blocker(s), rerun deterministic Phase 0 qualification, and restore a review candidate.\n\n**In scope:** the blocker IDs in `PROJECT_STATE.json`; Phase 0 qualification only.\n\n**Out of scope:** Phase 1 implementation; future features; unrelated refactors; production credentials/effects.\n\n**Required inputs:** controlling specification; current `PROJECT_STATE.json`; Phase 0 evidence and exact upstream pins.\n\n**Required outputs:** corrected deterministic Phase 0 qualification evidence or a precise remaining blocker.\n\n**Acceptance tests:** all Phase 0 deterministic gates pass; no new scope.\n\n**Package required?** yes when local mutation is needed\n\n**Next task on success:** `LAC-P0-REVIEW`.\n"""
    (ROOT/'PROJECT_STATE.json').write_text(json.dumps(state,indent=2)+'\n')
    (ROOT/'tasks'/'ACTIVE_TASK.md').write_text(active)

def main():
    if os.geteuid()==0: raise GateError('Phase 0 qualification must run as an unprivileged user, not root')
    for cmd in ['git','python3']:
        need(shutil.which(cmd) is not None, f'missing required command: {cmd}')
    data=json.loads(CANDIDATES_FILE.read_text())
    result={'schema':'lac.phase0-qualification/v1','started_at':now(),'status':'RUNNING','candidates':[],'airlock_test':None,'blockers':[],'nonblocking_findings':[]}
    lock={'schema':'lac.upstream-lock/v1','status':'QUALIFICATION_RUNNING','observed_date':'2026-09-05','qualified_at':None,'policy':'Exact checked-out commit LICENSE controls. Qualification does not incorporate upstream source.','upstreams':[]}

    def qualify_item(item, run_component_check=True):
        print(f"==> Fetching {item['repo']} @ {item['sha']}", flush=True)
        dest=clone_exact(item)
        lic=detect_license(dest)
        if item['expected_license']=='UNRESOLVED':
            if lic['family']!='UNRESOLVED':
                result['nonblocking_findings'].append(f"{item['key']}: root license now detected as {lic['family']}; code reuse remains disabled until a deliberate requalification decision.")
        else:
            need(lic['family']==item['expected_license'],f"{item['key']}: expected {item['expected_license']} license, found {lic['family']}")
        ver=observed_version(dest)
        tag=stable_tag(item['repo'])
        probe=probe_airlock(dest) if item['key']=='airlock' else probe_secondary(item['key'],dest)
        component_check=lightweight_source_test(item['key'],dest) if run_component_check else {'kind':'DEFERRED','status':'NOT_RUN'}
        bm=build_metadata(dest)
        ent={**item,'source_url':'https://github.com/'+item['repo'],'checkout_sha':item['sha'],'license_verified': item['expected_license']!='UNRESOLVED' and lic['family']==item['expected_license'], 'license_file':lic['file'],'license_family':lic['family'],'license_sha256':lic['sha256'],'observed_version':ver or item.get('expected_version'),'observed_stable_tag':tag,'build_metadata':bm,'qualification_status':'PASS','probe':probe,'component_check':component_check}
        lock['upstreams'].append(ent)
        result['candidates'].append({'key':item['key'],'sha':item['sha'],'license':lic,'version':ver,'stable_tag':tag,'build_metadata':bm,'probe':probe,'component_check':component_check})
        return dest

    try:
        items={x['key']:x for x in data['candidates']}
        # Airlock is the adoption decision gate. Complete its code trace and targeted upstream tests first.
        airlock_dest=qualify_item(items['airlock'],run_component_check=False)
        print('==> Running targeted Airlock upstream tests', flush=True)
        result['airlock_test']=test_airlock(airlock_dest)
        # Then perform the bounded secondary comparison required by Phase 0.
        for item in data['candidates']:
            if item['key']=='airlock': continue
            qualify_item(item,run_component_check=True)
        lock['status']='QUALIFIED'
        lock['qualified_at']=now()
        result['status']='PASS'; result['completed_at']=now()
        result['nonblocking_findings'].append('Waggle remains concepts-only/no-code-reuse while authoritative reuse licensing is unresolved or requires deliberate requalification.')
        write_state('PASS',[],result['nonblocking_findings'])
    except Exception as e:
        msg=f"LAC-P0-QUAL-001: {type(e).__name__}: {e}"
        result['status']='BLOCKED'; result['completed_at']=now(); result['blockers']=[msg]
        lock['status']='BLOCKED'; lock['qualified_at']=now()
        write_state('BLOCKED',[msg],result.get('nonblocking_findings',[]))
        (ROOT/'UPSTREAM_LOCK.json').write_text(json.dumps(lock,indent=2)+'\n')
        (EVIDENCE_DIR/'phase0.json').write_text(json.dumps(result,indent=2)+'\n')
        (EVIDENCE_DIR/'phase0.txt').write_text('STATUS=BLOCKED\nBLOCKER='+msg+'\n')
        print(msg, file=sys.stderr)
        return 1
    (ROOT/'UPSTREAM_LOCK.json').write_text(json.dumps(lock,indent=2)+'\n')
    (EVIDENCE_DIR/'phase0.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['STATUS=PASS','AIRLOCK_DISPOSITION=AIRLOCK_WRAPPED','PHASE_STATUS=CANDIDATE_FOR_INDEPENDENT_REVIEW']
    for e in lock['upstreams']:
        lines.append(f"UPSTREAM {e['key']} SHA={e['checkout_sha']} LICENSE={e['license_family']} LICENSE_SHA256={e['license_sha256'] or 'NONE'} VERSION={e['observed_version'] or 'UNKNOWN'} TAG={e['observed_stable_tag'] or 'NONE'}")
    (EVIDENCE_DIR/'phase0.txt').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines), flush=True)
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except GateError as e:
        print(f'LAC-P0-QUAL-BOOTSTRAP: {e}', file=sys.stderr); sys.exit(1)
