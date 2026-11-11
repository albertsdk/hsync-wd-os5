# Contributing to hsync-wd-os5

Thanks for your interest in contributing! This repository builds the HSYNC
package for **WD My Cloud OS5**: the `packaging/Apkg` tree (lifecycle scripts +
PHP/JS web UI) and the build pipeline that freezes the client and signs the
`.bin` with `mksapkg-OS5`.

## Prerequisites

- Python `>=3.12` with a virtualenv at `.venv/` (pytest + ruff; not committed)
- `php` on `PATH` (the web-UI endpoints are exercised by the test suite)
- Sibling checkouts of [`hsync-client`](../hsync-client) and
  [`hsync-common`](../hsync-common) — the packaged engine is **built from
  them**, never vendored
- Docker with `qemu-user-static` (binfmt) for the ARMv7 models
- Network access on the first build: the builder images come from Docker Hub
  and `mksapkg-OS5` is fetched from WDCommunity/wdpksrc

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pytest ruff pytest-cov pre-commit
```

## Tests and lint

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

The suite is the contract for this repository: it checks that the web form, the
PHP whitelists and the service launcher agree on the `HSYNC_*` key set, that
every locale carries the same dictionary keys, and that the packaged version
can only be the bundled engine version.

## Building the `.bin`

```bash
./compile.sh                              # all 10 models (ARMv7 + amd64)
./compile.sh --target wd-ex2-ultra-os5    # EX2 Ultra only (ARMv7)
./compile.sh --clean                      # remove dist/, build/ and the images
./compile.sh -v 1.2.0                     # pin the packaged version
```

`compile.sh` stages `../hsync-client` and `../hsync-common` into a minimal
Docker context, builds the Debian 10 (buster, glibc 2.28) image per CPU family,
runs PyInstaller inside it, then packages `packaging/Apkg` with `mksapkg-OS5`
in a separate `debian:bullseye` container (the tool needs `libxml2.so.2` and
`openssl bf-cbc`).

The packaged version defaults to the client version and must match
`hsync_common.constants::HSYNC_VERSION`; only a suffix (`-alpha.1`, `+build.7`)
may be added. Output:

- `dist/wd-ex2-ultra-os5/MyCloudEX2Ultra_hsync_<ver>.bin`
- `dist/wd-os5/<MODEL>_hsync_<ver>.bin` (one per model)

The source `Apkg/` tree is never mutated: staging happens in `build/`.

## Release

The release workflow (`.github/workflows/release.yml`) publishes the `.bin`
installers and always packages an **explicit engine ref**:

- **tag push** `vX.Y.Z` — the engine comes from the matching `hsync-client` tag
  `vX.Y.Z`; the job fails when that tag is missing or its version differs from
  the tag.
- **workflow_dispatch** — the `client_ref` input selects the engine ref (tag or
  branch, default `main`); `version_suffix` appends a suffix such as `-dev`
  (allowed only on top of the engine version).

Both jobs check out `hsync-client` and `hsync-common` with
`secrets.HSYNC_COMMON_PAT` because those repositories are private.

### Create a release

This repository declares **no version of its own**: the packaged version is
always the bundled `hsync-client` version, so a release only sets the tag —
there is no version bump to commit here.

1. Ensure the working tree is clean and on `main`.
2. Make sure the matching `hsync-client` tag `vX.Y.Z` exists: the workflow
   checks it out as the engine ref and fails when the tag's version differs
   from the client's. Publish the client release first if needed.
3. Tag the commit and push the tag:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. The `release.yml` workflow runs automatically: it gates on lint+test,
   builds all 10 model `.bin` packages (4 ARMv7 + 6 amd64) with
   `./compile.sh --target wd-os5-all`, generates `SHA256SUMS`, and creates the
   GitHub Release with auto-generated release notes.
5. Verify the release on the
   [Releases page](https://github.com/albertsdk/hsync-wd-os5/releases).

> You can also trigger a build-only run (no tag, no Release) or a Release from
> a different engine ref via `workflow_dispatch` on the Actions tab — useful
> for testing packaging changes without cutting a release. A
> `vX.Y.Z-<prerelease>` tag produces a GitHub prerelease (never `latest`), as
> in the other HSYNC projects.

### Post-release checklist

- [ ] All model `.bin` packages and `SHA256SUMS` are uploaded to the release
- [ ] A `.bin` is installed and smoke-tested on a WD My Cloud OS5 unit
- [ ] Release notes are published on GitHub

## Changing the web UI or the launcher

Any change to a CLI flag, an `HSYNC_*` variable or a user-facing default must
land atomically in:

- `packaging/Apkg/start.sh` (env → CLI flags, exported variables)
- `packaging/Apkg/install.sh` (seeded `hsync.env`)
- `packaging/Apkg/web/{index.html,app.js,config_get.php,config_set.php}`
- `packaging/Apkg/web/i18n/*.json` — every language offered by `SUPPORTED`
  in `app.js`
- `docs/configuration.md`

The event/flag contract itself is owned by `hsync-client`: update it there
first, then mirror it here in the same change set.

## Documentation

The user documentation in `docs/` must stay in sync with the code.

## Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): summary` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, …).

## Pull requests

- Keep changes focused and covered by tests.
- Ensure `pytest`, `ruff check` and `ruff format --check` pass locally.
- Do not commit `dist/`, `build/`, `packaging/.cache/` or any `.bin`.
