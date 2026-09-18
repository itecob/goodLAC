from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

RELEASE_VERSION = "1.0.0-rc.1"
RELEASE_SCHEMA = "lac.v1-product-release/v1"
CONFIG_SCHEMA = "lac.v1-owner-config/v1"
INSTALL_SCHEMA = "lac.v1-install-state/v1"
CONFIG_KEYS = ("workspace", "state", "trace", "pi_checkout", "runtime")
BIN_NAMES = ("lac-pi", "lacctl", "lac-owner", "lac-config", "lac-doctor")


class ProductizationError(RuntimeError):
    pass


def _run(args: list[str], *, cwd: Path | None = None, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(args, cwd=cwd, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        detail = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")[-4000:]
        raise ProductizationError(f"command failed ({proc.returncode}): {' '.join(args)}\n{detail}")
    return proc.stdout


def _strict_json_load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ProductizationError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductizationError(f"invalid JSON file: {path}") from exc


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ProductizationError(f"expected real directory: {path}")
    path.chmod(0o700)
    return path


def _write_private_json(path: Path, value: Any) -> None:
    _private_dir(path.parent)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, path)


def paths(home: Path | None = None) -> dict[str, Path]:
    h = (home or Path.home()).expanduser().resolve()
    return {
        "home": h,
        "share": h / ".local/share/local-agent-controller",
        "releases": h / ".local/share/local-agent-controller/releases",
        "distributions": h / ".local/share/local-agent-controller/distributions",
        "current": h / ".local/share/local-agent-controller/current",
        "bin": h / ".local/bin",
        "config": h / ".config/local-agent-controller/v1/config.json",
        "install_state": h / ".local/state/local-agent-controller/install/v1.json",
        "backup_root": h / ".local/state/local-agent-controller/backups/v1-productization",
        "controller_state": h / ".local/state/local-agent-controller/pi-v1/controller.db",
    }


def default_config(home: Path | None = None) -> dict[str, Any]:
    p = paths(home)
    return {
        "schema": CONFIG_SCHEMA,
        "workspace": str(p["home"] / ".local/share/local-agent-controller/pi-v1-workspace"),
        "state": str(p["controller_state"]),
        "trace": str(p["home"] / ".local/state/local-agent-controller/pi-v1/effect-trace.jsonl"),
        "pi_checkout": str(p["home"] / ".cache/local-agent-controller/phase0/upstream/pi"),
        "runtime": "manage",
    }


def validate_config(value: Any, home: Path | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema", *CONFIG_KEYS}:
        raise ProductizationError("config fields are invalid")
    if value.get("schema") != CONFIG_SCHEMA:
        raise ProductizationError("unsupported config schema")
    out = dict(value)
    for key in ("workspace", "state", "trace", "pi_checkout"):
        raw = out.get(key)
        if not isinstance(raw, str) or not raw or raw != raw.strip() or "\x00" in raw:
            raise ProductizationError(f"config {key} must be a non-empty path string")
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            raise ProductizationError(f"config {key} must be absolute")
        out[key] = str(candidate)
    if out.get("runtime") not in {"manage", "external"}:
        raise ProductizationError("config runtime must be manage or external")
    return out


def load_config(home: Path | None = None, *, create: bool = True) -> dict[str, Any]:
    p = paths(home)
    if not p["config"].exists():
        value = default_config(home)
        if create:
            _write_private_json(p["config"], value)
        return value
    info = p["config"].lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ProductizationError("owner config must be a real regular file")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ProductizationError("owner config must not grant group/other permissions")
    return validate_config(_strict_json_load(p["config"]), home)


def set_config(key: str, value: str, home: Path | None = None) -> dict[str, Any]:
    if key not in CONFIG_KEYS:
        raise ProductizationError(f"unsupported config key: {key}")
    config = load_config(home)
    config[key] = value
    config = validate_config(config, home)
    _write_private_json(paths(home)["config"], config)
    return config


def _git_index_entries(repo: Path) -> list[tuple[str, int]]:
    raw = _run(["git", "ls-files", "-s", "-z"], cwd=repo)
    entries: list[tuple[str, int]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode = int(meta.split()[0], 8)
        path = name.decode("utf-8", errors="strict")
        if path.startswith(".git/"):
            raise ProductizationError("git index unexpectedly contains .git material")
        entries.append((path, mode))
    if not entries:
        raise ProductizationError("git index is empty")
    return sorted(entries)


def _tar_add_bytes(tf: tarfile.TarFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mode = mode & 0o777
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    tf.addfile(info, io.BytesIO(data))


def _wrapper(command: str) -> bytes:
    body = f'''#!/usr/bin/env bash\nset -euo pipefail\nSELF="$(readlink -f "$0")"\nROOT="$(cd "$(dirname "$SELF")/.." && pwd)"\nAPP="$ROOT/app"\nexec python3 "$APP/scripts/lac-v1" {command} "$@"\n'''
    return body.encode("utf-8")


def build_distribution(repo: Path, output: Path) -> str:
    repo = repo.resolve(strict=True)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"local-agent-controller-{RELEASE_VERSION}"
    entries = _git_index_entries(repo)
    metadata = {
        "schema": RELEASE_SCHEMA,
        "version": RELEASE_VERSION,
        "source_head": _run(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip(),
        "source_index_tree": _run(["git", "write-tree"], cwd=repo).decode().strip(),
        "authority_note": "Packaging and owner UX are non-authoritative; canonical authority remains in LAC.",
        "persistent_service_autostart": False,
    }
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                for rel, mode in entries:
                    data = _run(["git", "show", f":{rel}"], cwd=repo)
                    _tar_add_bytes(tf, f"{prefix}/app/{rel}", data, 0o755 if mode & 0o111 else 0o644)
                for name, command in {
                    "lac-pi": "pi",
                    "lacctl": "ctl",
                    "lac-owner": "owner",
                    "lac-config": "config",
                    "lac-doctor": "doctor",
                }.items():
                    _tar_add_bytes(tf, f"{prefix}/bin/{name}", _wrapper(command), 0o755)
                _tar_add_bytes(tf, f"{prefix}/VERSION.json", (json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return digest


def _safe_extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        roots: set[str] = set()
        for member in members:
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts or not p.parts:
                raise ProductizationError("distribution archive contains unsafe path")
            if not (member.isdir() or member.isfile()):
                raise ProductizationError("distribution archive contains unsupported link/device")
            roots.add(p.parts[0])
        if len(roots) != 1:
            raise ProductizationError("distribution archive must contain exactly one root")
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                target.chmod(member.mode & 0o777)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tf.extractfile(member)
            if src is None:
                raise ProductizationError("distribution archive regular file has no payload")
            target.write_bytes(src.read())
            target.chmod(member.mode & 0o777)
    return destination / next(iter(roots))


def _copy_sqlite_backup(source: Path, target: Path) -> None:
    if not source.exists():
        return
    import sqlite3
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        dst = sqlite3.connect(target)
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        target.chmod(0o600)
    except sqlite3.Error as exc:
        raise ProductizationError("controller database backup failed; install aborted") from exc


def install_distribution(archive: Path, home: Path | None = None) -> dict[str, Any]:
    p = paths(home)
    archive = archive.expanduser().resolve(strict=True)
    tracked_dirs = [
        p["home"] / ".local", p["home"] / ".local/share", p["share"], p["releases"], p["distributions"], p["bin"],
        p["home"] / ".config", p["config"].parent.parent, p["config"].parent,
        p["home"] / ".local/state", p["home"] / ".local/state/local-agent-controller",
        p["install_state"].parent, p["home"] / ".local/state/local-agent-controller/backups", p["backup_root"],
    ]
    preexisting_dirs = {str(path): path.exists() for path in tracked_dirs}
    previous_current = None
    if p["current"].is_symlink():
        previous_current = os.readlink(p["current"])
        for name in BIN_NAMES:
            dest = p["bin"] / name
            if not dest.is_symlink():
                raise ProductizationError(f"supported prior install requires {dest} to be a symlink")
    elif p["current"].exists():
        raise ProductizationError("current install pointer must be a symlink")
    else:
        collisions = [str(p["bin"] / name) for name in BIN_NAMES if (p["bin"] / name).exists() or (p["bin"] / name).is_symlink()]
        if collisions:
            raise ProductizationError(f"install would overwrite non-LAC command paths: {collisions}")
    previous_config = p["config"].read_bytes() if p["config"].exists() else None
    previous_config_mode = stat.S_IMODE(p["config"].stat().st_mode) if p["config"].exists() else None
    target = p["releases"] / RELEASE_VERSION
    distribution_copy = p["distributions"] / f"local-agent-controller-{RELEASE_VERSION}.tar.gz"
    if target.exists() or target.is_symlink():
        raise ProductizationError(f"release target already exists: {target}")
    if distribution_copy.exists() or distribution_copy.is_symlink():
        raise ProductizationError(f"distribution archive target already exists: {distribution_copy}")

    # Validate the complete archive before creating installation state.
    extract_tmp = tempfile.TemporaryDirectory(prefix="lac-v1-extract-")
    root = _safe_extract(archive, Path(extract_tmp.name))
    meta = _strict_json_load(root / "VERSION.json")
    if not isinstance(meta, dict) or meta.get("schema") != RELEASE_SCHEMA or meta.get("version") != RELEASE_VERSION:
        extract_tmp.cleanup()
        raise ProductizationError("distribution metadata is invalid")

    backup_dir: Path | None = None
    staged = p["releases"] / (RELEASE_VERSION + ".staging")
    config_created = previous_config is None

    def restore_partial() -> None:
        p["current"].unlink(missing_ok=True)
        if previous_current:
            p["current"].parent.mkdir(parents=True, exist_ok=True)
            p["current"].symlink_to(previous_current)
        for name in BIN_NAMES:
            dest = p["bin"] / name
            dest.unlink(missing_ok=True)
            if previous_current:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.symlink_to(p["current"] / "bin" / name)
        if previous_config is None:
            p["config"].unlink(missing_ok=True)
        else:
            p["config"].parent.mkdir(parents=True, exist_ok=True)
            p["config"].write_bytes(previous_config)
            p["config"].chmod(previous_config_mode or 0o600)
        if target.exists(): shutil.rmtree(target)
        if staged.exists(): shutil.rmtree(staged)
        distribution_copy.unlink(missing_ok=True)
        p["install_state"].unlink(missing_ok=True)
        if backup_dir is not None and backup_dir.exists(): shutil.rmtree(backup_dir)
        for path in sorted((Path(k) for k, existed in preexisting_dirs.items() if existed is False), key=lambda x: len(x.parts), reverse=True):
            try: path.rmdir()
            except OSError: pass

    try:
        _private_dir(p["share"]); _private_dir(p["releases"]); _private_dir(p["distributions"]); _private_dir(p["bin"])
        _private_dir(p["config"].parent); _private_dir(p["backup_root"]); _private_dir(p["install_state"].parent)
        stamp = hashlib.sha256((str(archive) + str(os.getpid())).encode()).hexdigest()[:16]
        backup_dir = p["backup_root"] / stamp
        _private_dir(backup_dir)
        if previous_config is not None:
            (backup_dir / "config.json").write_bytes(previous_config)
            (backup_dir / "config.json").chmod(previous_config_mode or 0o600)
        _copy_sqlite_backup(p["controller_state"], backup_dir / "controller.db")
        shutil.copytree(root, staged, symlinks=False)
        os.replace(staged, target)
        load_config(home, create=True)
        shutil.copy2(archive, distribution_copy)
        distribution_copy.chmod(0o600)
        tmp_link = p["current"].with_name("current.tmp")
        tmp_link.unlink(missing_ok=True)
        tmp_link.symlink_to(target)
        os.replace(tmp_link, p["current"])
        for name in BIN_NAMES:
            dest = p["bin"] / name
            temp = p["bin"] / (name + ".tmp")
            temp.unlink(missing_ok=True)
            temp.symlink_to(p["current"] / "bin" / name)
            os.replace(temp, dest)
        state = {
            "schema": INSTALL_SCHEMA,
            "version": RELEASE_VERSION,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "release_dir": str(target),
            "distribution_archive": str(distribution_copy),
            "previous_current": previous_current,
            "backup_dir": str(backup_dir),
            "config_created": config_created,
            "previous_config_mode": previous_config_mode,
            "preexisting_dirs": preexisting_dirs,
            "database_migrated": False,
            "persistent_service_autostart": False,
        }
        _write_private_json(p["install_state"], state)
        return state
    except BaseException:
        restore_partial()
        raise
    finally:
        extract_tmp.cleanup()

def rollback(home: Path | None = None) -> dict[str, Any]:
    p = paths(home)
    if not p["install_state"].exists():
        raise ProductizationError("no v1 installation rollback record exists")
    state = _strict_json_load(p["install_state"])
    if not isinstance(state, dict) or state.get("schema") != INSTALL_SCHEMA:
        raise ProductizationError("installation rollback record is invalid")
    if state.get("database_migrated") is not False:
        raise ProductizationError("unsupported database migration state; fail closed")
    previous = state.get("previous_current")
    p["current"].unlink(missing_ok=True)
    if previous:
        p["current"].symlink_to(previous)
    for name in BIN_NAMES:
        dest = p["bin"] / name
        dest.unlink(missing_ok=True)
        if previous:
            dest.symlink_to(p["current"] / "bin" / name)
    backup_dir = Path(str(state.get("backup_dir", "")))
    if state.get("config_created") is True:
        p["config"].unlink(missing_ok=True)
    elif (backup_dir / "config.json").exists():
        p["config"].parent.mkdir(parents=True, exist_ok=True)
        p["config"].write_bytes((backup_dir / "config.json").read_bytes())
        p["config"].chmod(int(state.get("previous_config_mode") or 0o600))
    release = Path(str(state.get("release_dir", "")))
    if release.exists() and release.name == RELEASE_VERSION and release.parent == p["releases"]:
        shutil.rmtree(release)
    distribution_archive = Path(str(state.get("distribution_archive", "")))
    if distribution_archive.exists() and distribution_archive.parent == p["distributions"]:
        distribution_archive.unlink()
    p["install_state"].unlink(missing_ok=True)
    if backup_dir.exists() and backup_dir.parent == p["backup_root"]:
        shutil.rmtree(backup_dir)
    preexisting = state.get("preexisting_dirs")
    if isinstance(preexisting, dict):
        for path in sorted((Path(k) for k, existed in preexisting.items() if existed is False), key=lambda x: len(x.parts), reverse=True):
            try: path.rmdir()
            except OSError: pass
    return {"rolled_back": True, "restored_current": previous}


def current_app(home: Path | None = None) -> Path:
    p = paths(home)
    try:
        current = p["current"].resolve(strict=True)
    except OSError as exc:
        raise ProductizationError("LAC v1 is not installed") from exc
    app = current / "app"
    if not app.is_dir():
        raise ProductizationError("installed app directory is unavailable")
    return app


def _exec(argv: list[str], env: dict[str, str] | None = None) -> int:
    os.execvpe(argv[0], argv, os.environ if env is None else env)
    return 127


def launch_pi(home: Path | None, extra: list[str]) -> int:
    config = load_config(home)
    app = current_app(home)
    env = dict(os.environ)
    env["LAC_PI_CHECKOUT"] = config["pi_checkout"]
    argv = [
        "python3", str(app / "scripts/pi_v1_terminal.py"),
        "--workspace", config["workspace"], "--state", config["state"],
        "--trace", config["trace"], "--runtime", config["runtime"], *extra,
    ]
    return _exec(argv, env)


def launch_ctl(home: Path | None, extra: list[str]) -> int:
    return _exec(["python3", str(current_app(home) / "scripts/lacctl"), *extra])


def owner_command(home: Path | None, extra: list[str]) -> int:
    if not extra or extra[0] in {"help", "--help", "-h"}:
        print("lac-owner commands: pending, approvals, permissions, skills, emergency")
        print("These are thin aliases over the accepted owner-only lacctl administration API.")
        return 0
    group = extra[0]
    if group not in {"pending", "approvals", "permissions", "skills", "emergency"}:
        raise ProductizationError("unsupported owner command")
    return launch_ctl(home, extra)


def doctor(home: Path | None = None, *, static_only: bool = False) -> dict[str, Any]:
    app = current_app(home)
    config = load_config(home)
    checks: dict[str, Any] = {
        "schema": "lac.v1-doctor/v1", "version": RELEASE_VERSION,
        "linux": sys.platform.startswith("linux"), "python": sys.version_info >= (3, 10),
        "config": True, "persistent_service_autostart": False,
        "ordinary_standalone_pi_is_governed": False,
    }
    for binary in ("git", "node", "bwrap"):
        checks[binary] = shutil.which(binary) is not None
    if not static_only:
        env = dict(os.environ); env["LAC_PI_CHECKOUT"] = config["pi_checkout"]
        for script, key in (("verify_pi_pin.py", "pi_pin"), ("verify_freetoken_pin.py", "freetoken_pin")):
            proc = subprocess.run(["python3", str(app / "scripts" / script)], cwd=app, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
            checks[key] = proc.returncode == 0
    positive = {k: v for k, v in checks.items() if k not in {"schema", "version", "persistent_service_autostart", "ordinary_standalone_pi_is_governed"}}
    checks["ok"] = all(v is True for v in positive.values()) and checks["persistent_service_autostart"] is False and checks["ordinary_standalone_pi_is_governed"] is False
    return checks


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lac-v1", description="LAC v1 non-authoritative productization/owner UX")
    p.add_argument("--home", type=Path)
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("build"); q.add_argument("--output", required=True, type=Path); q.add_argument("--repo", type=Path)
    q = sub.add_parser("install"); q.add_argument("--archive", required=True, type=Path)
    sub.add_parser("rollback")
    q = sub.add_parser("config"); qs = q.add_subparsers(dest="config_command", required=True); qs.add_parser("show"); s=qs.add_parser("set"); s.add_argument("key", choices=CONFIG_KEYS); s.add_argument("value")
    q = sub.add_parser("doctor"); q.add_argument("--static", action="store_true")
    q = sub.add_parser("pi"); q.add_argument("args", nargs=argparse.REMAINDER)
    q = sub.add_parser("ctl"); q.add_argument("args", nargs=argparse.REMAINDER)
    q = sub.add_parser("owner"); q.add_argument("args", nargs=argparse.REMAINDER)
    return p


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    home = a.home.expanduser().resolve() if a.home else None
    if a.command == "build":
        repo = (a.repo or Path(__file__).resolve().parents[2]).resolve()
        print(json.dumps({"archive": str(a.output.resolve()), "sha256": build_distribution(repo, a.output)}, sort_keys=True)); return 0
    if a.command == "install": print(json.dumps(install_distribution(a.archive, home), sort_keys=True)); return 0
    if a.command == "rollback": print(json.dumps(rollback(home), sort_keys=True)); return 0
    if a.command == "config":
        value = load_config(home) if a.config_command == "show" else set_config(a.key, a.value, home)
        print(json.dumps(value, sort_keys=True, indent=2)); return 0
    if a.command == "doctor":
        value = doctor(home, static_only=a.static); print(json.dumps(value, sort_keys=True, indent=2)); return 0 if value["ok"] else 1
    if a.command == "pi": return launch_pi(home, a.args)
    if a.command == "ctl": return launch_ctl(home, a.args)
    if a.command == "owner": return owner_command(home, a.args)
    raise ProductizationError("unsupported command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProductizationError as exc:
        print(f"lac-v1: {exc}", file=sys.stderr)
        raise SystemExit(2)
