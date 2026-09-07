#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=['README.md','PROJECT_STATE.json','UPSTREAM_LOCK.json','THIRD_PARTY_NOTICES.md','docs/PROJECT_CHARTER.md','docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md','docs/ARCHITECTURE.md','docs/THREAT_MODEL.md','docs/CONTRACTS.md','docs/BUILD_REUSE_MATRIX.md','docs/UPSTREAM_QUALIFICATION.md','docs/TEST_STRATEGY.md','decisions/ADR-001_AIRLOCK_ADOPTION_STRATEGY.md','tasks/ACTIVE_TASK.md','qualification/evidence/phase0.json','qualification/evidence/phase0.txt']
missing=[x for x in required if not (ROOT/x).is_file()]
if missing:
    print('MISSING='+','.join(missing)); sys.exit(1)
state=json.loads((ROOT/'PROJECT_STATE.json').read_text())
lock=json.loads((ROOT/'UPSTREAM_LOCK.json').read_text())
ev=json.loads((ROOT/'qualification/evidence/phase0.json').read_text())
assert state['phase']=='PHASE_0_UPSTREAM_QUALIFICATION'
assert state['phase_status']=='CANDIDATE_FOR_INDEPENDENT_REVIEW'
assert state['active_task']=='LAC-P0-REVIEW'
assert not state['blockers']
assert lock['status']=='QUALIFIED'
assert ev['status']=='PASS'
up={x['key']:x for x in lock['upstreams']}
assert up['airlock']['phase0_disposition']=='AIRLOCK_WRAPPED'
assert up['airlock']['checkout_sha']=='68a71c7f0139c823971b95a79cf800e837630d3a'
assert up['airlock']['license_family']=='MIT'
assert up['pi']['license_family']=='MIT'
assert up['freetoken']['license_family']=='Apache-2.0'
assert up['waggle']['phase0_disposition']=='IDEAS_ONLY_NO_CODE_REUSE'
adr=(ROOT/'decisions/ADR-001_AIRLOCK_ADOPTION_STRATEGY.md').read_text()
assert 'AIRLOCK_WRAPPED' in adr
# Phase 0 must not contain implementation packages for authority/effects.
for banned in ['packages/core','packages/dispatcher','packages/effects','packages/adapters/pi']:
    assert not (ROOT/banned).exists(), f'future-phase implementation present: {banned}'
print('LAC_PROJECT_VERIFY=PASS')
print('PHASE=PHASE_0_UPSTREAM_QUALIFICATION')
print('PHASE_STATUS=CANDIDATE_FOR_INDEPENDENT_REVIEW')
print('AIRLOCK_DISPOSITION=AIRLOCK_WRAPPED')
print('NEXT_ACTION='+state['next_action'])
