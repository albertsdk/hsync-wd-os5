# Build module (`compile.sh`)

Single bash entry point with the monorepo's uniform surface (`-c/--clean`,
`-t/--target`, `-v/--version`, `-h/--help`) and a documented deviation: there is
no `native` target, because every artifact is a NAS package whose glibc ceiling
is the firmware's, not the host's. The default target is `wd-os5-all`.

## Symbols

| Symbol | Role |
| --- | --- |
| `compile.sh::CLIENT_DIR`, `compile.sh::COMMON_DIR` | sibling checkouts (`../hsync-client`, `../hsync-common`) |
| `compile.sh::get_version` | `-v` > `HSYNC_VERSION` > client `pyproject.toml` |
| `compile.sh::_verify_embedded_version` | client version == `HSYNC_VERSION`; only a suffix may be added |
| `compile.sh::check_prerequisites` | sibling trees present + Docker reachable |
| `compile.sh::qemu_handler_active`, `compile.sh::ensure_qemu_binfmt` | binfmt registration for the ARMv7 emulation (docker image pinned by digest) |
| `compile.sh::_stage_context` | minimal Docker context (`hsync-client/` + `hsync-common/`, `__pycache__` pruned) |
| `compile.sh::_docker_build` | builder image per CPU family, `BASE_IMAGE`/`TARGET_PLATFORM` as build args |
| `compile.sh::_run_pyinstaller_in_docker` | `pyinstaller` inside the image, running as the host uid, output mounted at `/out` |
| `compile.sh::PYINSTALLER_COMMON_FLAGS` | hidden imports / excludes shared by every model build |
| `compile.sh::_stage_package_tree` | disposable Apkg copy + icon + rendered `packaging/Apkg/apkg.rc` + `VERSION` |
| `compile.sh::_install_binary` | copies the `--onedir` bundle to `bin/<APP_NAME>/` |
| `compile.sh::_mksapkg_tool` | downloads `mksapkg-OS5` into `packaging/.cache/` on first use |
| `compile.sh::_build_mksapkg_image` | bullseye image that can execute the tool (`libxml2.so.2`, `openssl bf-cbc`) |
| `compile.sh::_run_mksapkg` | runs the tool with the staging parent mounted at `/work` |
| `compile.sh::_wdos5_package_model` | stage + pack one model, normalise the `.bin` name |
| `compile.sh::build_wd_os5` / `compile.sh::build_wd_os5_all` | the two targets |
| `compile.sh::clean_artifacts`, `compile.sh::clean_images` | `--clean` (dist/, build/, local images) |

## Why the context is staged

The frozen engine must match the workspace. Docker cannot see outside its
context, so `_stage_context` materialises exactly the manifests, sources and
README needed by `packaging/Dockerfile.builder`:

- `hsync-client/{pyproject.toml,poetry.lock,README.md,hsync_client}`
- `hsync-common/{pyproject.toml,README.md,hsync_common}`

The builder image installs dependencies in a cached layer keyed on the manifests
only, then bakes the sources as cheap layers: editing client code does not
re-run the slow ARMv7 native builds (cryptography/Rust, zstandard, the
PyInstaller bootloader).

## Determinism and cleanup

- mksapkg-OS5 appends the build date to the file name; `_wdos5_package_model`
  renames the artifact to `<MODEL>_hsync_<version>.bin`.
- Stale `.bin` files in the staging parent are removed before each packaging run.
- Everything produced by PyInstaller goes to `build/`; the source tree stays
  clean (`packaging/Apkg` is only ever copied).
- Docker images are built locally and never published
  (`hsync-wdos5-builder:*`, `hsync-wdos5-mksapkg:bullseye`).

## Release pipeline (`.github/workflows/release.yml`)

`gate` (ruff, shell syntax, tests) → `packages` (all models) → `release`
(`.bin` + `SHA256SUMS` attached to the release). The engine ref is explicit:
the matching `hsync-client` tag on a tag push, the `client_ref` input on a
dispatch. The version is read from that checkout and
`compile.sh::_verify_embedded_version` enforces the coupling, so a `.bin` can
never advertise a version its engine does not report.

## Tests guarding this module

`tests/test_packaging_contract.py` asserts the option surface, the default
target, the version sourcing (no version in this repository), the staged
directory name, the icon copy, the model/CPU split, the gitignore rules, and
exercises `get_version` / `_verify_embedded_version` by sourcing the script.
