#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, signal, sys
from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0,str(REPO_ROOT))
from packages.admin import AdminRequest, AdminService, UnixAdminServer
from packages.adapters.pi.production import PI_V1_CAPABILITY_MANIFEST
from packages.state import SQLiteStateStore
_stop=False
def _stop_now(_s,_f):
    global _stop; _stop=True
def _parent_alive(pid):
    try: os.kill(pid,0); return pid>1
    except (ProcessLookupError,PermissionError): return False
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state",required=True,type=Path)
    p.add_argument("--parent-pid",required=True,type=int)
    a=p.parse_args()
    signal.signal(signal.SIGTERM,_stop_now); signal.signal(signal.SIGINT,_stop_now)
    store=SQLiteStateStore(a.state.expanduser().resolve(strict=True))
    service=AdminService(store,owner_uid=os.getuid())
    bootstrap=AdminRequest.create(
        request_id="admin:pi-v1:bootstrap-register",
        operation="skills.register",
        arguments={"manifest":PI_V1_CAPABILITY_MANIFEST},
    )
    registration=service.execute(bootstrap,peer_uid=os.getuid())
    server=UnixAdminServer(service)
    try:
        socket_path=server.start()
        print(json.dumps({
            "schema":"lac.pi-v1-admin-ready/v1","pid":os.getpid(),
            "socket":str(socket_path),"state":str(store.path),
            "registered_application_id":registration["application_id"],
            "registered_skill_id":registration["skill_id"]
        },sort_keys=True),flush=True)
        while not _stop and _parent_alive(a.parent_pid):
            server.serve_once(timeout=0.5)
        return 0
    finally:
        server.close(); store.close()
if __name__=="__main__": raise SystemExit(main())
