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
from typing import Any, Iterable, Mapping

RELEASE_VERSION = "1.0.0-rc.10"
RELEASE_SCHEMA = "lac.v1-product-release/v1"
CONFIG_SCHEMA = "lac.v1-owner-config/v1"
INSTALL_SCHEMA = "lac.v1-install-state/v1"
CONFIG_KEYS = ("workspace", "state", "trace", "pi_checkout", "runtime")
BIN_NAMES = ("pi", "lac-pi", "lacctl", "lac-owner", "lac-config", "lac-doctor")
TAKEOVER_BIN_NAMES = ("pi",)
DANGEROUS_BYPASS_FLAG = "--dangerously-bypass-lac"
PINNED_PI_SOURCE_CLI_REL = Path("packages/coding-agent/src/cli.ts")
PINNED_PI_ROOT_TSCONFIG_REL = Path("tsconfig.json")
PINNED_PI_CODING_AGENT_PACKAGE_REL = Path("packages/coding-agent/package.json")
PINNED_PI_TSX_CANDIDATES = (
    Path("node_modules/tsx/dist/cli.mjs"),
    Path("node_modules/tsx/dist/cli.cjs"),
    Path("node_modules/.bin/tsx"),
)
SHELL_BLOCK_START = "# >>> Local Agent Controller default-governed pi >>>"
SHELL_BLOCK_END = "# <<< Local Agent Controller default-governed pi <<<"
SHELL_FRAGMENT_REL = ".config/local-agent-controller/shell/pi.sh"
FISH_FRAGMENT_REL = ".config/fish/conf.d/90-lac-default-pi.fish"
LAUNCHER_PROBE_ENV = "LAC_PI004_INTERNAL_LAUNCHER_PROBE"
LAUNCHER_PROBE_VALUE = "default-governed-v1"
LAUNCHER_PROBE_MARKER = "LAC_PI004_GOVERNED_LAUNCHER=PASS"


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
                    "pi": "pi",
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


def _capture_external_bin(path: Path) -> tuple[dict[str, Any], bytes | None]:
    if path.is_symlink():
        return {"kind": "symlink", "target": os.readlink(path)}, None
    if not path.exists():
        return {"kind": "absent"}, None
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ProductizationError(f"cannot take over unsupported command path: {path}")
    return {"kind": "file", "mode": stat.S_IMODE(info.st_mode)}, path.read_bytes()


def _restore_external_bin(path: Path, material: Mapping[str, Any], data: bytes | None = None, backup: Path | None = None) -> None:
    path.unlink(missing_ok=True)
    kind = material.get("kind")
    if kind == "absent":
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "symlink":
        target = material.get("target")
        if not isinstance(target, str) or not target:
            raise ProductizationError("external command symlink backup is malformed")
        path.symlink_to(target)
        return
    if kind == "file":
        payload = data
        if payload is None and backup is not None:
            payload = backup.read_bytes()
        if payload is None:
            raise ProductizationError("external command file backup is unavailable")
        path.write_bytes(payload)
        path.chmod(int(material.get("mode") or 0o700))
        return
    raise ProductizationError("external command backup kind is invalid")


def _target_shell() -> str:
    override = os.environ.get("LAC_PI004_TARGET_SHELL")
    raw = override or os.environ.get("SHELL") or "/bin/bash"
    name = Path(raw).name
    if name not in {"bash", "zsh", "fish"}:
        raise ProductizationError(f"unsupported owner shell for default Pi integration: {name}")
    return name


def _shell_paths(home: Path | None = None) -> dict[str, Path | str | None]:
    h = (home or Path.home()).expanduser().resolve()
    shell = _target_shell()
    if shell == "bash":
        return {"shell": shell, "rc": h / ".bashrc", "fragment": h / SHELL_FRAGMENT_REL}
    if shell == "zsh":
        return {"shell": shell, "rc": h / ".zshrc", "fragment": h / SHELL_FRAGMENT_REL}
    return {"shell": shell, "rc": None, "fragment": h / FISH_FRAGMENT_REL}


def _shell_fragment_bytes(shell: str, pi_launcher: Path) -> bytes:
    launcher = str(pi_launcher.expanduser().absolute())
    if shell in {"bash", "zsh"}:
        return (
            "# Managed by Local Agent Controller.\n"
            "pi() {\n"
            f"  command {json.dumps(launcher)} \"$@\"\n"
            "}\n"
        ).encode("utf-8")
    if shell == "fish":
        escaped = launcher.replace("\\", "\\\\").replace('"', '\\"')
        return (
            "# Managed by Local Agent Controller.\n"
            "function pi\n"
            f"    command \"{escaped}\" $argv\n"
            "end\n"
        ).encode("utf-8")
    raise ProductizationError("unsupported shell integration")


def _shell_rc_block(fragment: Path) -> bytes:
    q = json.dumps(str(fragment.expanduser().absolute()))
    return (
        f"{SHELL_BLOCK_START}\n"
        f"if [ -r {q} ]; then\n"
        f"  . {q}\n"
        "fi\n"
        f"{SHELL_BLOCK_END}\n"
    ).encode("utf-8")


def _install_shell_integration(home: Path | None, pi_launcher: Path) -> dict[str, Any]:
    paths_ = _shell_paths(home)
    shell = str(paths_["shell"])
    fragment = Path(paths_["fragment"])
    rc_raw = paths_["rc"]
    fragment.parent.mkdir(parents=True, exist_ok=True)
    if fragment.parent.is_symlink() or not fragment.parent.is_dir():
        raise ProductizationError("shell integration directory must be a real directory")
    fragment.write_bytes(_shell_fragment_bytes(shell, pi_launcher))
    fragment.chmod(0o600)
    if rc_raw is not None:
        rc = Path(rc_raw)
        if rc.exists() and (rc.is_symlink() or not rc.is_file()):
            raise ProductizationError("shell rc must be a real regular file when present")
        before = rc.read_bytes() if rc.exists() else b""
        block = _shell_rc_block(fragment)
        start_count = before.count(SHELL_BLOCK_START.encode())
        end_count = before.count(SHELL_BLOCK_END.encode())
        if start_count or end_count:
            if start_count != 1 or end_count != 1 or block not in before:
                raise ProductizationError("pre-existing LAC shell marker is malformed or unmanaged; fail closed")
        else:
            rc.parent.mkdir(parents=True, exist_ok=True)
            sep = b"" if not before or before.endswith(b"\n") else b"\n"
            rc.write_bytes(before + sep + block)
            if not before:
                rc.chmod(0o600)
    return {"shell": shell, "rc_path": str(rc_raw) if rc_raw is not None else None, "fragment_path": str(fragment)}


def _shell_integration_configured(home: Path | None, pi_launcher: Path) -> bool:
    try:
        paths_ = _shell_paths(home)
    except ProductizationError:
        return False
    shell = str(paths_["shell"])
    fragment = Path(paths_["fragment"])
    if not fragment.is_file() or fragment.is_symlink() or fragment.read_bytes() != _shell_fragment_bytes(shell, pi_launcher):
        return False
    rc_raw = paths_["rc"]
    if rc_raw is None:
        return True
    rc = Path(rc_raw)
    if not rc.is_file() or rc.is_symlink():
        return False
    return _shell_rc_block(fragment) in rc.read_bytes()


def install_distribution(archive: Path, home: Path | None = None) -> dict[str, Any]:
    p = paths(home)
    archive = archive.expanduser().resolve(strict=True)
    shell_paths = _shell_paths(home)
    shell_rc = Path(shell_paths["rc"]) if shell_paths["rc"] is not None else None
    shell_fragment = Path(shell_paths["fragment"])
    tracked_dirs = [
        p["home"] / ".local", p["home"] / ".local/share", p["share"], p["releases"], p["distributions"], p["bin"],
        p["home"] / ".config", p["config"].parent.parent, p["config"].parent,
        p["home"] / ".local/state", p["home"] / ".local/state/local-agent-controller",
        p["install_state"].parent, p["home"] / ".local/state/local-agent-controller/backups", p["backup_root"],
        shell_fragment.parent,
    ]
    if shell_rc is not None:
        tracked_dirs.append(shell_rc.parent)
    preexisting_dirs = {str(path): path.exists() for path in tracked_dirs}
    previous_shell_rc, previous_shell_rc_bytes = _capture_external_bin(shell_rc) if shell_rc is not None else ({"kind":"absent"}, None)
    previous_shell_fragment, previous_shell_fragment_bytes = _capture_external_bin(shell_fragment)
    previous_current = None
    previous_managed_bins: list[str] = []
    previous_external_bins: dict[str, dict[str, Any]] = {}
    previous_external_bytes: dict[str, bytes] = {}

    if p["current"].is_symlink():
        previous_current = os.readlink(p["current"])
        try:
            previous_release = p["current"].resolve(strict=True)
        except OSError as exc:
            raise ProductizationError("prior LAC current pointer is broken") from exc
        for name in BIN_NAMES:
            prior_command = previous_release / "bin" / name
            dest = p["bin"] / name
            if prior_command.is_file():
                if not dest.is_symlink() or dest.resolve(strict=True) != prior_command.resolve(strict=True):
                    raise ProductizationError(f"supported prior install requires managed symlink {dest}")
                previous_managed_bins.append(name)
            elif dest.exists() or dest.is_symlink():
                if name not in TAKEOVER_BIN_NAMES:
                    raise ProductizationError(f"install would overwrite non-LAC command path: {dest}")
                material, data = _capture_external_bin(dest)
                previous_external_bins[name] = material
                if data is not None:
                    previous_external_bytes[name] = data
    elif p["current"].exists():
        raise ProductizationError("current install pointer must be a symlink")
    else:
        for name in BIN_NAMES:
            dest = p["bin"] / name
            if not (dest.exists() or dest.is_symlink()):
                continue
            if name not in TAKEOVER_BIN_NAMES:
                raise ProductizationError(f"install would overwrite non-LAC command path: {dest}")
            material, data = _capture_external_bin(dest)
            previous_external_bins[name] = material
            if data is not None:
                previous_external_bytes[name] = data

    previous_config = p["config"].read_bytes() if p["config"].exists() else None
    previous_config_mode = stat.S_IMODE(p["config"].stat().st_mode) if p["config"].exists() else None
    previous_install_state = p["install_state"].read_bytes() if p["install_state"].exists() else None
    previous_install_state_mode = stat.S_IMODE(p["install_state"].stat().st_mode) if p["install_state"].exists() else None
    if previous_current is not None and previous_install_state is None:
        raise ProductizationError("prior LAC release pointer exists without install-state record")

    target = p["releases"] / RELEASE_VERSION
    distribution_copy = p["distributions"] / f"local-agent-controller-{RELEASE_VERSION}.tar.gz"
    if target.exists() or target.is_symlink():
        raise ProductizationError(f"release target already exists: {target}")
    if distribution_copy.exists() or distribution_copy.is_symlink():
        raise ProductizationError(f"distribution archive target already exists: {distribution_copy}")

    extract_tmp = tempfile.TemporaryDirectory(prefix="lac-v1-extract-")
    root = _safe_extract(archive, Path(extract_tmp.name))
    meta = _strict_json_load(root / "VERSION.json")
    if not isinstance(meta, dict) or meta.get("schema") != RELEASE_SCHEMA or meta.get("version") != RELEASE_VERSION:
        extract_tmp.cleanup()
        raise ProductizationError("distribution metadata is invalid")

    backup_dir: Path | None = None
    staged = p["releases"] / (RELEASE_VERSION + ".staging")
    config_created = previous_config is None
    install_state_replaced = False
    shell_mutated = False

    def restore_bins(*, use_backup: bool) -> None:
        for name in BIN_NAMES:
            (p["bin"] / name).unlink(missing_ok=True)
        if previous_current:
            for name in previous_managed_bins:
                dest = p["bin"] / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.symlink_to(p["current"] / "bin" / name)
        for name, material in previous_external_bins.items():
            backup = (backup_dir / f"external-bin-{name}") if use_backup and backup_dir is not None else None
            _restore_external_bin(p["bin"] / name, material, previous_external_bytes.get(name), backup)

    def restore_install_state(*, use_backup: bool) -> None:
        if previous_install_state is None:
            if install_state_replaced:
                p["install_state"].unlink(missing_ok=True)
            return
        payload = previous_install_state
        if use_backup and backup_dir is not None:
            candidate = backup_dir / "previous-install-state"
            if candidate.is_file():
                payload = candidate.read_bytes()
        p["install_state"].parent.mkdir(parents=True, exist_ok=True)
        p["install_state"].write_bytes(payload)
        p["install_state"].chmod(previous_install_state_mode or 0o600)

    def restore_shell(*, use_backup: bool) -> None:
        nonlocal shell_mutated
        if not shell_mutated:
            return
        if shell_rc is not None:
            _restore_external_bin(shell_rc, previous_shell_rc, previous_shell_rc_bytes,
                                  (backup_dir / "previous-shell-rc") if use_backup and backup_dir is not None else None)
        _restore_external_bin(shell_fragment, previous_shell_fragment, previous_shell_fragment_bytes,
                              (backup_dir / "previous-shell-fragment") if use_backup and backup_dir is not None else None)
        shell_mutated = False

    def restore_partial() -> None:
        p["current"].unlink(missing_ok=True)
        if previous_current:
            p["current"].parent.mkdir(parents=True, exist_ok=True)
            p["current"].symlink_to(previous_current)
        restore_bins(use_backup=False)
        restore_shell(use_backup=False)
        if previous_config is None:
            p["config"].unlink(missing_ok=True)
        else:
            p["config"].parent.mkdir(parents=True, exist_ok=True)
            p["config"].write_bytes(previous_config)
            p["config"].chmod(previous_config_mode or 0o600)
        restore_install_state(use_backup=False)
        if target.exists(): shutil.rmtree(target)
        if staged.exists(): shutil.rmtree(staged)
        distribution_copy.unlink(missing_ok=True)
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
        if previous_install_state is not None:
            prior = backup_dir / "previous-install-state"
            prior.write_bytes(previous_install_state)
            prior.chmod(previous_install_state_mode or 0o600)
        for name, material in previous_external_bins.items():
            if material.get("kind") == "file":
                target_backup = backup_dir / f"external-bin-{name}"
                target_backup.write_bytes(previous_external_bytes[name])
                target_backup.chmod(int(material.get("mode") or 0o700))
        if shell_rc is not None and previous_shell_rc.get("kind") == "file":
            assert previous_shell_rc_bytes is not None
            q=backup_dir / "previous-shell-rc"; q.write_bytes(previous_shell_rc_bytes); q.chmod(int(previous_shell_rc.get("mode") or 0o600))
        if previous_shell_fragment.get("kind") == "file":
            assert previous_shell_fragment_bytes is not None
            q=backup_dir / "previous-shell-fragment"; q.write_bytes(previous_shell_fragment_bytes); q.chmod(int(previous_shell_fragment.get("mode") or 0o600))
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
        shell_mutated = True
        shell_state = _install_shell_integration(home, p["bin"] / "pi")
        state = {
            "schema": INSTALL_SCHEMA,
            "version": RELEASE_VERSION,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "release_dir": str(target),
            "distribution_archive": str(distribution_copy),
            "previous_current": previous_current,
            "previous_managed_bins": previous_managed_bins,
            "previous_external_bins": previous_external_bins,
            "backup_dir": str(backup_dir),
            "config_created": config_created,
            "previous_config_mode": previous_config_mode,
            "previous_install_state_present": previous_install_state is not None,
            "previous_install_state_mode": previous_install_state_mode,
            "shell_integration": {
                **shell_state,
                "previous_rc": previous_shell_rc if shell_rc is not None else None,
                "previous_fragment": previous_shell_fragment,
            },
            "preexisting_dirs": preexisting_dirs,
            "database_migrated": False,
            "persistent_service_autostart": False,
        }
        _write_private_json(p["install_state"], state)
        install_state_replaced = True
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
    previous_managed = state.get("previous_managed_bins")
    previous_external = state.get("previous_external_bins")
    if not isinstance(previous_managed, list) or any(not isinstance(v, str) for v in previous_managed):
        raise ProductizationError("installation rollback managed-bin record is invalid")
    if not isinstance(previous_external, dict):
        raise ProductizationError("installation rollback external-bin record is invalid")
    backup_dir = Path(str(state.get("backup_dir", "")))
    shell_state = state.get("shell_integration")
    if not isinstance(shell_state, dict):
        raise ProductizationError("installation rollback shell-integration record is invalid")
    raw_fragment=shell_state.get("fragment_path"); raw_rc=shell_state.get("rc_path")
    previous_fragment=shell_state.get("previous_fragment"); previous_rc=shell_state.get("previous_rc")
    if not isinstance(raw_fragment,str) or not isinstance(previous_fragment,dict):
        raise ProductizationError("installation rollback shell integration is malformed")
    fragment=Path(raw_fragment).expanduser().resolve()
    expected=_shell_paths(home)
    if fragment != Path(expected["fragment"]).resolve():
        raise ProductizationError("installation rollback shell fragment path mismatch")
    rc: Path | None = None
    if expected["rc"] is not None:
        if not isinstance(raw_rc,str) or not isinstance(previous_rc,dict):
            raise ProductizationError("installation rollback shell rc material is malformed")
        rc=Path(raw_rc).expanduser().resolve()
        if rc != Path(expected["rc"]).resolve():
            raise ProductizationError("installation rollback shell rc path mismatch")

    p["current"].unlink(missing_ok=True)
    if previous:
        p["current"].symlink_to(previous)
    for name in BIN_NAMES:
        (p["bin"] / name).unlink(missing_ok=True)
    if previous:
        for name in previous_managed:
            (p["bin"] / name).symlink_to(p["current"] / "bin" / name)
    for name, material in previous_external.items():
        if not isinstance(name, str) or not isinstance(material, dict):
            raise ProductizationError("installation rollback external-bin material is invalid")
        _restore_external_bin(p["bin"] / name, material, backup=backup_dir / f"external-bin-{name}")

    if rc is not None and previous_rc is not None:
        _restore_external_bin(rc, previous_rc, backup=backup_dir / "previous-shell-rc")
    _restore_external_bin(fragment, previous_fragment, backup=backup_dir / "previous-shell-fragment")

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

    if state.get("previous_install_state_present") is True:
        prior = backup_dir / "previous-install-state"
        if not prior.is_file():
            raise ProductizationError("prior install-state backup is missing; fail closed")
        p["install_state"].write_bytes(prior.read_bytes())
        p["install_state"].chmod(int(state.get("previous_install_state_mode") or 0o600))
    else:
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


def _resolve_pinned_pi_source_cli(checkout: Path) -> tuple[Path, Path, Path]:
    checkout = checkout.expanduser().resolve(strict=True)
    source = checkout / PINNED_PI_SOURCE_CLI_REL
    tsconfig = checkout / PINNED_PI_ROOT_TSCONFIG_REL
    package = checkout / PINNED_PI_CODING_AGENT_PACKAGE_REL
    for path, label in ((source, "source CLI"), (tsconfig, "root tsconfig"), (package, "coding-agent package metadata")):
        if not path.is_file() or path.is_symlink():
            raise ProductizationError(f"pinned Pi {label} unavailable: {path}")
    try:
        metadata = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductizationError("pinned Pi coding-agent metadata is unreadable") from exc
    if metadata.get("version") != "0.85.1":
        raise ProductizationError(f"unexpected pinned Pi coding-agent version: {metadata.get('version')!r}")

    for rel in PINNED_PI_TSX_CANDIDATES:
        candidate = checkout / rel
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        try:
            resolved.relative_to(checkout)
        except ValueError:
            continue
        if resolved.is_file():
            return source, resolved, tsconfig
    raise ProductizationError("checkout-local tsx runtime required for pinned Pi source CLI is unavailable")


def _verify_and_launch_pinned_ungoverned_pi(app: Path, config: Mapping[str, Any], extra: list[str], env: dict[str, str]) -> int:
    verify = subprocess.run(
        ["python3", str(app / "scripts/verify_pi_pin.py")],
        cwd=app,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if verify.returncode != 0:
        raise ProductizationError(f"pinned Pi verification failed before dangerous bypass: {verify.stdout[-1600:]}")
    checkout = Path(str(config["pi_checkout"])).expanduser().resolve(strict=True)
    source_cli, tsx_cli, root_tsconfig = _resolve_pinned_pi_source_cli(checkout)
    node = shutil.which("node")
    if not node:
        raise ProductizationError("Node.js is required for pinned Pi dangerous bypass")
    node_path = Path(node).resolve(strict=True)
    print(
        "WARNING: --dangerously-bypass-lac disables Local Agent Controller governance, "
        "including LAC approval/policy enforcement and the governed sandbox for this top-level Pi session.",
        file=sys.stderr,
        flush=True,
    )
    return _exec(
        [str(node_path), str(tsx_cli), "--tsconfig", str(root_tsconfig), str(source_cli), *extra],
        env,
    )


def launch_pi(home: Path | None, extra: list[str]) -> int:
    if os.environ.get(LAUNCHER_PROBE_ENV) == LAUNCHER_PROBE_VALUE:
        print(LAUNCHER_PROBE_MARKER)
        return 0
    config = load_config(home)
    app = current_app(home)
    env = dict(os.environ)
    env["LAC_PI_CHECKOUT"] = config["pi_checkout"]
    if extra and extra[0] == DANGEROUS_BYPASS_FLAG:
        return _verify_and_launch_pinned_ungoverned_pi(app, config, extra[1:], env)
    argv = [
        "python3", str(app / "scripts/pi_native_tui_host.py"),
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
    p = paths(home)
    user_pi = p["bin"] / "pi"
    direct_governed = user_pi.is_symlink() and user_pi.resolve() == p["current"].joinpath("bin", "pi").resolve()
    shell_override_configured = _shell_integration_configured(home, user_pi)
    checks: dict[str, Any] = {
        "schema": "lac.v1-doctor/v1", "version": RELEASE_VERSION,
        "linux": sys.platform.startswith("linux"), "python": sys.version_info >= (3, 10),
        "config": True, "persistent_service_autostart": False,
        "default_pi_is_governed": direct_governed and shell_override_configured,
        "shell_override_configured": shell_override_configured,
        "owner_shell": _target_shell(),
        "dangerous_bypass_is_explicit": True,
    }
    for binary in ("git", "node", "bwrap", "fd", "rg"):
        checks[binary] = shutil.which(binary) is not None
    if not static_only:
        env = dict(os.environ); env["LAC_PI_CHECKOUT"] = config["pi_checkout"]
        for script, key in (("verify_pi_pin.py", "pi_pin"), ("verify_freetoken_pin.py", "freetoken_pin")):
            proc = subprocess.run(["python3", str(app / "scripts" / script)], cwd=app, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
            checks[key] = proc.returncode == 0
    positive = {k: v for k, v in checks.items() if k not in {"schema", "version", "persistent_service_autostart", "owner_shell"}}
    checks["ok"] = all(v is True for v in positive.values()) and checks["persistent_service_autostart"] is False
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
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "pi":
        return launch_pi(None, raw[1:])
    if raw and raw[0] == "ctl":
        return launch_ctl(None, raw[1:])
    if raw and raw[0] == "owner":
        return owner_command(None, raw[1:])
    if len(raw) >= 3 and raw[0] == "--home" and raw[2] == "pi":
        return launch_pi(Path(raw[1]).expanduser().resolve(), raw[3:])
    if len(raw) >= 3 and raw[0] == "--home" and raw[2] == "ctl":
        return launch_ctl(Path(raw[1]).expanduser().resolve(), raw[3:])
    if len(raw) >= 3 and raw[0] == "--home" and raw[2] == "owner":
        return owner_command(Path(raw[1]).expanduser().resolve(), raw[3:])
    a = _parser().parse_args(raw)
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
