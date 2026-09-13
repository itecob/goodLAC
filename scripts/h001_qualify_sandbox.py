#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = "lac.sandbox-qualification/v1"
REQUIRED_CONTROLS = (
    "filesystem_visibility",
    "writable_paths",
    "process_isolation",
    "outbound_network",
    "environment_inheritance",
    "credential_exposure",
    "child_process_containment",
    "rootless_user_namespace",
    "lifecycle_cleanup",
    "failure_mode",
)


def run(argv: list[str], *, env: dict[str, str] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            env=env,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": argv,
            "rc": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "seconds": round(time.monotonic() - started, 3),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "rc": 124,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "seconds": round(time.monotonic() - started, 3),
            "timeout": True,
        }


def copy_binary_and_libs(binary: Path, rootfs: Path) -> None:
    resolved = binary.resolve()
    destination = rootfs / resolved.relative_to("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved, destination)
    probe = run(["/usr/bin/ldd" if Path("/usr/bin/ldd").is_file() else "ldd", str(resolved)])
    if probe["rc"] != 0:
        raise RuntimeError(f"ldd failed for {resolved}: {probe['stderr']}")
    paths: set[Path] = set()
    for line in probe["stdout"].splitlines():
        for raw in re.findall(r"(?:=>\s*)?(/[^\s(]+)", line):
            candidate = Path(raw)
            if candidate.is_file():
                paths.add(candidate)
    for library in sorted(paths, key=str):
        dest = rootfs / library.relative_to("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(library, dest)


def build_runtime_root(base: Path) -> tuple[Path, str, str]:
    bash = shutil.which("bash")
    sleep = shutil.which("sleep")
    ldd = shutil.which("ldd")
    if not bash or not sleep or not ldd:
        raise RuntimeError("qualification requires local bash, sleep, and ldd")
    rootfs = base / "rootfs"
    rootfs.mkdir()
    # Bubblewrap cannot create later bind-mount targets beneath a root that
    # has already been mounted read-only. Create every H001 fixture target
    # in the runtime root before the read-only root bind is established.
    for name in ("proc", "dev", "tmp", "etc", "workspace", "workspace/ro", "workspace/rw"):
        (rootfs / name).mkdir(parents=True, exist_ok=True)
    copy_binary_and_libs(Path(bash), rootfs)
    copy_binary_and_libs(Path(sleep), rootfs)
    return rootfs, str(Path(bash).resolve()), str(Path(sleep).resolve())


def listener_probe(invoke) -> tuple[bool, dict[str, Any]]:
    accepted = {"value": False}
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.settimeout(2.0)
    port = server.getsockname()[1]

    def worker() -> None:
        try:
            conn, _addr = server.accept()
        except (socket.timeout, OSError):
            return
        accepted["value"] = True
        conn.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    result = invoke(f"exec 3<>/dev/tcp/127.0.0.1/{port}", timeout=4.0)
    thread.join(timeout=2.5)
    server.close()
    return (result["rc"] != 0 and not accepted["value"]), result


def process_namespace_probe(invoke, host_sleep: str) -> tuple[bool, dict[str, Any]]:
    host = subprocess.Popen([host_sleep, "20"])
    try:
        result = invoke(f"kill -0 {host.pid} 2>/dev/null && exit 91 || exit 0")
        return result["rc"] == 0, result
    finally:
        host.terminate()
        try:
            host.wait(timeout=2)
        except subprocess.TimeoutExpired:
            host.kill()
            host.wait(timeout=2)


def child_containment_probe(invoke, rw: Path, sleep_inside: str) -> tuple[bool, dict[str, Any]]:
    marker = rw / "outlived-sandbox"
    marker.unlink(missing_ok=True)
    # A child that remains alive after the sandbox's main process exits must not
    # retain access to the writable bind. Give an escaped child enough time to
    # create the marker before judging containment.
    script = f"({sleep_inside} 1; echo escaped > /workspace/rw/outlived-sandbox) & exit 0"
    result = invoke(script, timeout=3.0)
    time.sleep(1.5)
    return result["rc"] == 0 and not marker.exists(), result


def common_probe(invoke, ro: Path, rw: Path, outside_secret: Path, host_sleep: str, sleep_inside: str) -> tuple[dict[str, bool], dict[str, Any]]:
    probes: dict[str, Any] = {}
    controls = {name: False for name in REQUIRED_CONTROLS}

    smoke = invoke("IFS= read -r x < /workspace/ro/allowed.txt; test \"$x\" = ALLOWED; echo OK > /workspace/rw/write.txt")
    probes["smoke_rw"] = smoke
    controls["writable_paths"] = smoke["rc"] == 0 and (rw / "write.txt").is_file() and (rw / "write.txt").read_text().strip() == "OK"

    ro_probe = invoke("if echo forbidden > /workspace/ro/forbidden.txt 2>/dev/null; then exit 92; else exit 0; fi")
    probes["read_only_mount"] = ro_probe
    controls["filesystem_visibility"] = ro_probe["rc"] == 0 and not (ro / "forbidden.txt").exists()

    hidden = invoke(f"test ! -e {shlex_quote(str(outside_secret))}")
    probes["arbitrary_host_path_hidden"] = hidden
    controls["filesystem_visibility"] = controls["filesystem_visibility"] and hidden["rc"] == 0

    env = invoke(
        "test -z \"${LAC_H001_SECRET_SHOULD_NOT_LEAK+x}\" "
        "&& test -z \"${AWS_SECRET_ACCESS_KEY+x}\" "
        "&& test -z \"${SSH_AUTH_SOCK+x}\" "
        "&& test -z \"${HTTP_PROXY+x}\" "
        "&& test -z \"${HTTPS_PROXY+x}\""
    )
    probes["environment_clear"] = env
    controls["environment_inheritance"] = env["rc"] == 0
    controls["credential_exposure"] = env["rc"] == 0

    net_ok, net = listener_probe(invoke)
    probes["network_namespace"] = net
    controls["outbound_network"] = net_ok

    proc_ok, proc = process_namespace_probe(invoke, host_sleep)
    probes["process_namespace"] = proc
    controls["process_isolation"] = proc_ok

    child_ok, child = child_containment_probe(invoke, rw, sleep_inside)
    probes["child_containment"] = child
    controls["child_process_containment"] = child_ok

    return controls, probes


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def qualify_bubblewrap(rootfs: Path, bash_inside: str, sleep_inside: str, ro: Path, rw: Path, outside: Path) -> dict[str, Any]:
    binary = shutil.which("bwrap")
    result: dict[str, Any] = {
        "candidate": "bubblewrap",
        "binary": str(Path(binary).resolve()) if binary else None,
        "status": "FAIL",
        "disposition": "NOT_SELECTED",
        "controls": {name: False for name in REQUIRED_CONTROLS},
        "probes": {},
    }
    if not binary:
        result["availability"] = "UNAVAILABLE"
        result["reason"] = "bwrap binary not found"
        result["controls"]["failure_mode"] = True
        return result
    version = run([binary, "--version"])
    result["version"] = version
    if version["rc"] != 0 or os.geteuid() == 0:
        result["reason"] = "bubblewrap version probe failed or qualification was not rootless"
        result["controls"]["failure_mode"] = True
        return result

    base = [
        binary,
        "--unshare-user",
        "--unshare-pid",
        "--unshare-net",
        "--unshare-ipc",
        "--unshare-uts",
        "--cap-drop",
        "ALL",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--ro-bind",
        str(rootfs),
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        str(ro),
        "/workspace/ro",
        "--bind",
        str(rw),
        "/workspace/rw",
        "--chdir",
        "/workspace",
        "--setenv",
        "PATH",
        f"{Path(bash_inside).parent}:{Path(sleep_inside).parent}",
        "--setenv",
        "HOME",
        "/nonexistent",
        "--",
        bash_inside,
        "-c",
    ]

    def invoke(script: str, timeout: float = 10.0) -> dict[str, Any]:
        env = dict(os.environ)
        env["LAC_H001_SECRET_SHOULD_NOT_LEAK"] = "qualification-secret"
        env["AWS_SECRET_ACCESS_KEY"] = "qualification-secret"
        env["SSH_AUTH_SOCK"] = "/tmp/lac-h001-should-not-leak.sock"
        env["HTTP_PROXY"] = "http://127.0.0.1:9"
        env["HTTPS_PROXY"] = "http://127.0.0.1:9"
        return run(base + [script], env=env, timeout=timeout)

    controls, probes = common_probe(invoke, ro, rw, outside, shutil.which("sleep") or "/usr/bin/sleep", sleep_inside)
    controls["rootless_user_namespace"] = all(
        probes[name]["rc"] == 0 for name in ("smoke_rw", "environment_clear")
    ) and os.geteuid() != 0
    controls["lifecycle_cleanup"] = controls["child_process_containment"]
    controls["failure_mode"] = True
    result["controls"] = controls
    result["probes"] = probes
    result["status"] = "PASS" if all(controls.values()) else "FAIL"
    if result["status"] != "PASS":
        result["reason"] = "one or more required bubblewrap isolation probes failed"
    return result


def podman_rootless(binary: str) -> tuple[bool, dict[str, Any]]:
    probe = run([binary, "info", "--format", "json"], timeout=15.0)
    if probe["rc"] != 0:
        return False, probe
    try:
        data = json.loads(probe["stdout"])
    except json.JSONDecodeError:
        return False, probe
    host = data.get("host") or data.get("Host") or {}
    security = host.get("security") or host.get("Security") or {}
    value = security.get("rootless")
    if value is None:
        value = security.get("Rootless")
    return value is True, probe


def qualify_podman(rootfs: Path, bash_inside: str, sleep_inside: str, ro: Path, rw: Path, outside: Path) -> dict[str, Any]:
    binary = shutil.which("podman")
    result: dict[str, Any] = {
        "candidate": "rootless_podman",
        "binary": str(Path(binary).resolve()) if binary else None,
        "status": "FAIL",
        "disposition": "NOT_SELECTED",
        "controls": {name: False for name in REQUIRED_CONTROLS},
        "probes": {},
    }
    if not binary:
        result["availability"] = "UNAVAILABLE"
        result["reason"] = "podman binary not found"
        result["controls"]["failure_mode"] = True
        return result
    version = run([binary, "--version"])
    result["version"] = version
    is_rootless, info = podman_rootless(binary)
    result["rootless_info"] = info
    if not is_rootless or os.geteuid() == 0:
        result["reason"] = "podman is not operating rootlessly for the current user"
        result["controls"]["failure_mode"] = True
        return result

    name = f"lac-h001-qual-{os.getpid()}"
    base = [
        binary,
        "run",
        "--rm",
        "--name",
        name,
        "--read-only",
        "--network=none",
        "--http-proxy=false",
        "--no-hosts",
        "--no-hostname",
        "--pid=private",
        "--ipc=private",
        "--userns=keep-id",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m",
        "--mount",
        f"type=bind,src={ro},dst=/workspace/ro,ro=true",
        "--mount",
        f"type=bind,src={rw},dst=/workspace/rw",
        "--workdir",
        "/workspace",
        "--env",
        f"PATH={Path(bash_inside).parent}:{Path(sleep_inside).parent}",
        "--env",
        "HOME=/nonexistent",
        "--rootfs",
        str(rootfs),
        bash_inside,
        "-c",
    ]

    def invoke(script: str, timeout: float = 12.0) -> dict[str, Any]:
        env = dict(os.environ)
        env["LAC_H001_SECRET_SHOULD_NOT_LEAK"] = "qualification-secret"
        env["AWS_SECRET_ACCESS_KEY"] = "qualification-secret"
        env["SSH_AUTH_SOCK"] = "/tmp/lac-h001-should-not-leak.sock"
        env["HTTP_PROXY"] = "http://127.0.0.1:9"
        env["HTTPS_PROXY"] = "http://127.0.0.1:9"
        return run(base + [script], env=env, timeout=timeout)

    controls, probes = common_probe(invoke, ro, rw, outside, shutil.which("sleep") or "/usr/bin/sleep", sleep_inside)
    controls["rootless_user_namespace"] = is_rootless
    exists = run([binary, "container", "exists", name])
    probes["lifecycle_cleanup"] = exists
    controls["lifecycle_cleanup"] = exists["rc"] != 0 and controls["child_process_containment"]
    controls["failure_mode"] = True
    result["controls"] = controls
    result["probes"] = probes
    result["status"] = "PASS" if all(controls.values()) else "FAIL"
    if result["status"] != "PASS":
        result["reason"] = "one or more required rootless Podman isolation probes failed"
    return result


def sanitize_probe_commands(candidate: dict[str, Any]) -> None:
    for probe in candidate.get("probes", {}).values():
        if isinstance(probe, dict) and "argv" in probe:
            probe["argv"] = [Path(x).name if i == 0 else x for i, x in enumerate(probe["argv"])]
    for key in ("version", "rootless_info"):
        probe = candidate.get(key)
        if isinstance(probe, dict) and "argv" in probe:
            probe["argv"] = [Path(x).name if i == 0 else x for i, x in enumerate(probe["argv"])]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-text", required=True)
    args = parser.parse_args()

    observed = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "BLOCKED",
        "observed_at": observed,
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "euid": os.geteuid(),
        },
        "required_controls": list(REQUIRED_CONTROLS),
        "selection_policy": "Prefer bubblewrap when both established backends pass because it is the smaller direct namespace wrapper; otherwise select passing rootless Podman; select neither on incomplete guarantees.",
        "selected_backend": None,
        "candidates": {},
    }

    try:
        with tempfile.TemporaryDirectory(prefix="lac-h001-qual-") as tmp_raw:
            tmp = Path(tmp_raw)
            rootfs, bash_inside, sleep_inside = build_runtime_root(tmp)
            ro = tmp / "fixture-ro"
            rw = tmp / "fixture-rw"
            outside_dir = tmp / "outside"
            ro.mkdir()
            rw.mkdir()
            outside_dir.mkdir()
            (ro / "allowed.txt").write_text("ALLOWED\n", encoding="utf-8")
            outside = outside_dir / "secret.txt"
            outside.write_text("MUST_NOT_BE_VISIBLE\n", encoding="utf-8")

            bwrap = qualify_bubblewrap(rootfs, bash_inside, sleep_inside, ro, rw, outside)
            # Reset mutable fixture before the second candidate.
            for child in rw.iterdir():
                if child.is_file():
                    child.unlink()
            podman = qualify_podman(rootfs, bash_inside, sleep_inside, ro, rw, outside)
            sanitize_probe_commands(bwrap)
            sanitize_probe_commands(podman)
            evidence["candidates"] = {"bubblewrap": bwrap, "rootless_podman": podman}
    except Exception as exc:
        evidence["qualification_error"] = f"{type(exc).__name__}: {exc}"

    selected = None
    if evidence.get("candidates", {}).get("bubblewrap", {}).get("status") == "PASS":
        selected = "bubblewrap"
    elif evidence.get("candidates", {}).get("rootless_podman", {}).get("status") == "PASS":
        selected = "rootless_podman"
    if selected:
        evidence["status"] = "PASS"
        evidence["selected_backend"] = selected
        evidence["candidates"][selected]["disposition"] = "SELECTED"
        other = "rootless_podman" if selected == "bubblewrap" else "bubblewrap"
        if evidence["candidates"][other]["status"] == "PASS":
            evidence["candidates"][other]["disposition"] = "QUALIFIED_NOT_SELECTED"
        elif evidence["candidates"][other].get("availability") == "UNAVAILABLE":
            evidence["candidates"][other]["disposition"] = "UNAVAILABLE_NOT_SELECTED"
        else:
            evidence["candidates"][other]["disposition"] = "FAILED_NOT_SELECTED"
        evidence["selection_rationale"] = (
            "bubblewrap passed all required H001 controls and is the simpler established direct namespace backend"
            if selected == "bubblewrap"
            else "rootless Podman passed all required H001 controls; bubblewrap did not satisfy the complete local qualification gate"
        )
    else:
        for candidate in evidence.get("candidates", {}).values():
            if candidate.get("availability") == "UNAVAILABLE":
                candidate["disposition"] = "UNAVAILABLE_NOT_SELECTED"
            else:
                candidate["disposition"] = "FAILED_NOT_SELECTED"
        evidence["selection_rationale"] = "No established candidate satisfied every binding H001 isolation control; fail closed."

    output_json = Path(args.output_json)
    output_text = Path(args.output_text)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_text.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "LAC H001 Sandbox Qualification",
        f"STATUS={evidence['status']}",
        f"OBSERVED_AT={evidence['observed_at']}",
        f"SELECTED_BACKEND={evidence.get('selected_backend') or 'NONE'}",
    ]
    for key in ("bubblewrap", "rootless_podman"):
        candidate = evidence.get("candidates", {}).get(key, {})
        lines.append(f"{key.upper()}_STATUS={candidate.get('status', 'NOT_RUN')}")
        lines.append(f"{key.upper()}_DISPOSITION={candidate.get('disposition', 'NOT_SELECTED')}")
        failed = [name for name, value in candidate.get("controls", {}).items() if value is not True]
        lines.append(f"{key.upper()}_FAILED_CONTROLS={','.join(failed) if failed else 'NONE'}")
    lines.append(f"RATIONALE={evidence.get('selection_rationale', 'qualification error')}")
    output_text.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
