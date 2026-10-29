# Decisions

## ADR 001 — WD OS5 packaging lives in its own repository

**Context.** The packaging (Apkg tree + build + mksapkg tooling) used to live
in the client repository (`packaging/wd-os5`, removed) with its build targets
inside the client's `compile.sh`. It shares nothing with the client's CLI
packaging (`.deb`, `.rpm`, Raspberry Pi) except the binary, and it is the only
part that needs a Debian buster cross-build, a bullseye side-car container and a
vendor tool.

**Decision.** `hsync-wd-os5` is a standalone repository. It consumes the client
as **sources from a sibling checkout** and owns the whole `.bin` pipeline.

**Consequences.** The client repository has no WD-specific code or targets;
documentation, workflows and release assets for the NAS package live here.
`hsync-client` and `hsync-common` must be cloned as siblings to build.

## ADR 002 — The packaged version is the client version

**Context.** A `.bin` carries `packaging/Apkg/apkg.rc`'s `Version`, a `VERSION` file and the
file name, while the engine reports its own `HSYNC_VERSION`.

**Decision.** `compile.sh::get_version` reads the version from
`../hsync-client/pyproject.toml` (`-v` / `HSYNC_VERSION` override it) and
`compile.sh::_verify_embedded_version` refuses any base version that differs
from `hsync_common.constants::HSYNC_VERSION`. Only a suffix
(`-alpha.1`, `+build.7`) may be added. This repository declares no version of
its own.

**Consequences.** One place to bump; a stale or mixed checkout fails the build
instead of shipping a package whose dashboard version lies about its engine.

## ADR 003 — Debian 10 (buster) for both CPU families

**Context.** The stock OS5 firmware exposes glibc up to 2.30. A binary built on
a modern host fails with `GLIBC_X.XX not found`.

**Decision.** Both families (ARMv7 and amd64) are frozen in
`arm32v7/debian:buster` / `amd64/debian:buster`, even when the host is amd64.
`cryptography` needs OpenSSL ≥ 3 while buster ships 1.1.1, so the builder
compiles a static OpenSSL 3 (`packaging/Dockerfile.builder`).

**Consequences.** The amd64 build is containerized too, even though PyInstaller
runs natively there; the glibc ceiling, not the host architecture, decides.

## ADR 004 — mksapkg-OS5 runs inside a container

**Context.** The vendor tool is a prebuilt x86-64 binary linked against
`libxml2.so.2` that shells out to `openssl bf-cbc`. Modern hosts ship neither
(`libxml2.so.16`, OpenSSL 3 legacy provider).

**Decision.** `compile.sh::_build_mksapkg_image` builds a local
`debian:bullseye` image and `compile.sh::_run_mksapkg` executes the cached tool
there, with the staging parent mounted at `/work` and the host uid, because the
tool drops the artifact next to its CWD.

**Consequences.** The build works on any modern distribution; artifacts stay
caller-owned. The image is local-only and rebuilt by `--clean`.

## ADR 005 — One committed icon, copied at staging time

**Context.** `packaging/Apkg/apkg.rc` declares `Icon: hsync.png` (package root) while the web UI
serves `web/hsync.png`. A generator script produced the root copy in the past,
but nothing invoked it any more and the file was absent.

**Decision.** `packaging/Apkg/web/hsync.png` (160x160) is the single committed
source; `compile.sh::_stage_package_tree` copies it to the package root. It is
the shared HSYNC app icon, downscaled from the master
`branding/hsync-app-icon.png` (1024x1024, same geometry as the Android
adaptive icon), so every HSYNC application shows the same mark. The dead
generator script is removed (historical: it was never invoked) instead of
adding a Pillow
dependency to the build.

**Consequences.** No generated file in the source tree, no new build
dependency, and the metadata path always resolves.

## ADR 006 — The web UI owns the whole `hsync.env` file

**Context.** A partial update would let a removed key keep a stale value (for
example a trust pin).

**Decision.** `packaging/Apkg/web/config_set.php` iterates its `KEYS` whitelist and writes every key
on each Save; values are validated/clamped first.

**Consequences.** Manual edits to whitelisted keys are overwritten by a Save
from the UI, and a key with no form field falls back to its default.
