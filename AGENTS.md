# Project Rules & Coding Guidelines (hsync-wd-os5 — packaging)

This document defines the rules for the `hsync-wd-os5` repository: the WD My
Cloud OS5 package (`packaging/Apkg`) and the `compile.sh` pipeline that freezes
the client from the sibling `../hsync-client` checkout into a `.bin`.

> **Where this file comes from**: portable, self-contained copy of the rules for
> this repository. The canonical single source of truth for the HSYNC monorepo
> is the root `AGENTS.md` (which also drives `.clinerules/` via
> `scripts/dev/gen-clinerules.py`). Keep project-specific rules here; edit the
> root `AGENTS.md` for anything shared.

---

## 🗂️ Repository layout & git rules

| Path | Content |
|---|---|
| `packaging/Apkg/` | Package tree: `apkg.rc`, `env`, lifecycle `*.sh`, `web/` (PHP + JS + i18n), `web/hsync.png` |
| `packaging/Dockerfile.builder` | Debian buster + Python 3.12 + Poetry + static OpenSSL 3; builds the frozen client |
| `packaging/Dockerfile.mksapkg` | Debian bullseye runtime for the vendor `mksapkg-OS5` |
| `compile.sh` | The only build entry point (`wd-os5-all` default, `wd-ex2-ultra-os5`) |
| `tests/` | pytest suite: web UI/launcher checks + build contract |
| `llm-wiki/`, `docs/` | Agent wiki and user documentation (kept in sync) |

- This is its own git repository. Verify it with
  `git -C hsync-wd-os5 rev-parse --git-dir` before any git command; if the check
  fails, **stop and report it as a blocker** — never `git init`, never commit
  these files from another repository.
- Inspect what you are about to commit (`git status --short`,
  `git diff --cached`) and prefer explicit paths over `git add -A`.
- **Never commit** `dist/`, `build/`, `packaging/.cache/`, `*.bin`, `.venv/` or
  any `.env`-style secret file.
- Conventional Commits (`type(scope): description`), English only.

## ⚠️ Domain-critical rule — WD My Cloud OS5

Any change to a **CLI flag**, an **`HSYNC_*` variable** or a **user-facing
default** — wherever it originates (`hsync-client`, `hsync-common`, or this
repository) — **REQUIRES** a synchronized update to:

- `packaging/Apkg/start.sh` (env → flags, exported variables)
- `packaging/Apkg/install.sh` (seeded `hsync.env`)
- `packaging/Apkg/web/index.html`, `app.js`, `config_get.php`, `config_set.php`,
  `env_lib.php` and the action endpoints (`hsyncignore_*.php`, `trust.php`,
  `state_reset.php`, `test.php`, `ca_cert_upload.php`, `service.php`,
  `log_get.php`)
- `packaging/Apkg/web/i18n/*.json` — every language offered by `SUPPORTED` in
  `app.js`
- `docs/configuration.md`

Keep flags, key whitelists and i18n strings strictly aligned across every
language the selector offers. The client is the SSOT for flag semantics: change
it there first, then mirror it here in the same change set.

**Build invariants** (guarded by `tests/test_packaging_contract.py`):

- the packaged version is the client version and must equal
  `hsync_common.constants::HSYNC_VERSION` (only a suffix may be added);
- this repository declares no version of its own;
- the staged directory basename equals the package name (`APP_NAME`);
- `apkg.rc` keeps the `__HSYNC_VERSION__` placeholder and its icon resolves;
- `packaging/Apkg` is only ever copied — the source tree is never mutated.

## 📚 Documentation maintenance (Dual-Docs)

- **Docs-first**: read `llm-wiki/README.md`, then the relevant module page,
  before exploring or modifying code. Follow the `path/to/file::symbol`
  anchors; codebase-wide search is the fallback.
- **Dual sync**: any addition, modification or removal updates `llm-wiki/` and,
  when user-facing, `docs/` — in the same task. Never leave either stale.
- **Drift prevention**: reference symbols instead of restating values they own;
  never use line numbers; keep `architecture.md`/`modules/*` current-state only
  and delete prose that describes removed code.
- When a doc is added, renamed or deleted, update the relevant `README.md` index
  in the same change.

## ✅ Implementation quality gate

1. **Acceptance criteria first** — observable behaviour, failure/boundary paths,
   security implications (this package runs as root on a NAS and edits its own
   `hsync.env`), affected contracts, existing tests.
2. **Smallest complete change** — no speculative features, no broad `except`,
   no silent fallbacks, no weakening of tests.
3. **Verification pass** — re-read the request, inspect the complete diff, trace
   normal/invalid/empty/limit paths, then run:

   ```bash
   .venv/bin/python -m pytest -q
   .venv/bin/python -m ruff check .
   .venv/bin/python -m ruff format --check .
   bash -n compile.sh
   ```

   `php` is required by the behavioural endpoint tests; they skip when the CLI is
   absent, so a green run without PHP is not full coverage — say so.
   A real `.bin` build (`./compile.sh`) needs Docker, qemu-user-static and
   network access: if unavailable, report it as **not executed**, never as
   verified.
4. **Regression tests** — every fix ships a test that fails before it; new
   behaviour covers its success and failure paths. The suite verifies the
   package contract (assets, whitelists, launcher, version), not internal
   implementation details.
5. **Bounded correction cycle** — at most two review-and-correction rounds; do
   not finalize with known failures; report blockers precisely.

Final report: what changed, commands executed and their outcome, checks not
executed and why, remaining risks.

## 🐍 Python scope (tests only)

This repository ships no Python package: `pyproject.toml` holds tooling
configuration only. Rules for the test suite:

- use type hints and the `pathlib` API; no manual string parsing of files that
  a stdlib parser can read (e.g. `tomllib`);
- reuse helpers (`_php_keys`, `_supported_locales`, `_bash`) instead of
  copy-pasting parsing logic;
- tests must be deterministic and leave no artifacts behind (`tmp_path`;
  `build/` and `dist/` are never touched).

## 🧱 Build interface

`compile.sh` follows the monorepo's uniform surface — `-c/--clean`,
`-t/--target`, `-v/--version`, `-h/--help` — with one documented deviation:
there is no `native` target, because every artifact is a NAS package built
against the firmware's glibc (buster). Keep the shared helpers
(`qemu_handler_active`, `ensure_qemu_binfmt`, the logging helpers, the Docker
invocation style) structurally aligned with the other projects' `compile.sh`.

## 📝 Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/). Do not
edit it without explicit confirmation for the current task.
