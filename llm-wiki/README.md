# HSYNC WD OS5 — Agent Wiki (index)

Packaging repository for the **WD My Cloud OS5** app: it freezes the `hsync`
client from the sibling `../hsync-client` checkout and wraps it, together with
the `packaging/Apkg` tree (lifecycle shell scripts + PHP/JS web UI), into a
`.bin` installer produced by `mksapkg-OS5`.

It contains **no Python application code**: the only Python is the test suite
that guards the Apkg tree and the build contract.

> **Docs-first**: read this index and the relevant module page before touching
> code; follow the `path/to/file::symbol` anchors. End-user docs live in
> [`../docs/`](../docs/README.md) and must stay in sync (Dual-Docs rule).

## Map

| Doc | Scope |
| --- | --- |
| [architecture.md](architecture.md) | what a `.bin` contains, the two CPU families, build pipeline, runtime layout on the NAS, how the client is embedded |
| [modules/build.md](modules/build.md) | `compile.sh`: targets, version SSOT, sibling staging, Docker images, mksapkg runner |
| [modules/runtime.md](modules/runtime.md) | `packaging/Apkg/{env,preinst,install,postinst,init,start,stop,remove,clean}.sh`: lifecycle, env → CLI translation, security invariants |
| [modules/web-ui.md](modules/web-ui.md) | `packaging/Apkg/web`: endpoints, config flow, ignore/trust/probe/reset actions, connect-command generator, i18n |
| [data-models.md](data-models.md) | the `hsync.env` key model (web ↔ `packaging/Apkg/web/config_set.php` ↔ `packaging/Apkg/start.sh` ↔ client flags/env) and the package metadata |
| [decisions.md](decisions.md) | ADRs: separate repository, version follows the client, buster baseline, containerized mksapkg, icon source |

## Quick facts

- `APP_NAME` / package name: `hsync` (`packaging/Apkg/apkg.rc` `Package:`,
  `compile.sh::APP_NAME`).
- Build entry: `compile.sh` — default target `wd-os5-all`; single-model target
  `wd-ex2-ultra-os5`. There is no host/native artifact.
- Version SSOT: the frozen client (`../hsync-client/pyproject.toml`) which must
  equal `hsync_common.constants::HSYNC_VERSION`; enforced by
  `compile.sh::_verify_embedded_version`. A patch-level drift is a warning; a
  major/minor drift aborts. Only a suffix may otherwise be added on top.
- Model → CPU family map: `compile.sh::WDOS5_ARMV7_MODELS` /
  `compile.sh::WDOS5_AMD64_MODELS`.
- Outputs: `dist/wd-ex2-ultra-os5/<MODEL>_hsync_<ver>.bin`,
  `dist/wd-os5/<MODEL>_hsync_<ver>.bin`.
- Tests: `tests/test_wd_os5_web.py` (web UI + launcher static/behavioural
  checks, PHP endpoints executed when the CLI is present) and
  `tests/test_packaging_contract.py` (build/version/icon contract).

## Cross-repo SSOT

- CLI flags, `HSYNC_*` variables and their semantics are owned by
  `hsync-client` ([wiki](../../hsync-client/llm-wiki/README.md)).
- Shared constants (including `HSYNC_VERSION`) and the wire protocol are owned
  by `hsync-common` ([wiki](../../hsync-common/llm-wiki/README.md)).
- This repository only *mirrors* them into the NAS launcher, the web UI and the
  package. Never redefine a contract here.

## Conventions used in this wiki

- Every claim is anchored to code via `path::symbol`; no line numbers.
- No large code blocks are duplicated — intent is described and the code
  referenced.
- Kept in sync with `../docs/` per the Dual-Docs rule in the root `AGENTS.md`.
