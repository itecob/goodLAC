# Default-Governed Pi UX Roadmap

Owner authorization on 2026-09-19 opens a bounded post-v1 roadmap without reopening the accepted Phase 6 release candidate. `1.0.0-rc.1` remains the last independently accepted release while this line is implemented and reviewed.

Sequence:

1. `LAC-PI004` — make the ordinary installed `pi` entrypoint LAC-governed by default; preserve an explicit dangerous owner bypass; prove exact rc.1 rollback.
2. `LAC-PI005` — replace the custom governed terminal frontend with Pi's native TUI/session surface while retaining the same sandbox, four controller-backed consequential tools, owner-only administration and no-bypass boundary. Resource/extension loading must be explicitly qualified because Pi extensions execute inside the Pi process.
3. `LAC-PI006` — owner UAT and stabilization of the native governed Pi experience, including normal CLI/TUI invocation, permissions/approvals, restart behavior, and explicit dangerous bypass UX.
4. Fresh independent phase review — accept or block the resulting candidate.

No additional harness, model provider, compatibility facade, external product, authority-core redesign, or broader tool surface is authorized by this roadmap.

## Tool-manager PATH precedence

PI004 must also govern the ordinary interactive `pi` command when a tool manager such as mise places its managed Pi executable ahead of `~/.local/bin` in `PATH`. LAC therefore installs a bounded owner-shell override that calls `~/.local/bin/pi` by absolute path. The tool-manager installation and configuration are not modified or executed by PI004. The shell startup file and LAC shell fragment are backed up/restored exactly on rollback.
