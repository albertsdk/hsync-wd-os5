# Architecture

A `.bin` is a signed tar of one **staged package tree**: the committed
`packaging/Apkg` directory, the frozen client binary under
`bin/hsync/` (PyInstaller `--onedir`), an icon, the `LICENSE` (BSD-3-Clause
requires it with binary distributions) and a rendered
`packaging/Apkg/apkg.rc`.
`mksapkg-OS5` produces it; the OS5 dashboard validates `apkg.sign` at upload.

## Component map

| Layer | Code | Responsibility |
| --- | --- | --- |
| Build entry | `compile.sh::main` | parse `-c/-t/-v/-h`, dispatch to `build_wd_os5` or `build_wd_os5_all` |
| Source staging | `compile.sh::_stage_context` | copy `../hsync-client` + `../hsync-common` into the Docker context |
| Freezer | `compile.sh::_docker_build`, `compile.sh::_run_pyinstaller_in_docker` | build the buster image per CPU family and run PyInstaller inside it |
| Package staging | `compile.sh::_stage_package_tree`, `compile.sh::_install_binary` | disposable Apkg copy, icon, `VERSION`, rendered `packaging/Apkg/apkg.rc`, binary |
| Packer | `compile.sh::_run_mksapkg`, `compile.sh::_wdos5_package_model` | run `mksapkg-OS5` in a bullseye container and normalise the `.bin` name |
| Lifecycle | `packaging/Apkg/{preinst,install,postinst,init,start,stop,remove,clean}.sh` | install/upgrade/boot/service control on the NAS |
| Launcher | `packaging/Apkg/start.sh` | `hsync.env` → CLI flags + exported secrets, then start the daemon |
| Web UI | `packaging/Apkg/web/*` | configuration, service control, log, ignore list, trust store, probes, reset |

## How the client is embedded

Same contract as `hsync-desktop`: **sources from a sibling checkout**, never a
Poetry dependency and never an import of client internals from this repository.

```
compile.sh
  ├─ _stage_context  → build/wdos5/ctx/{hsync-client,hsync-common}   (manifests + sources)
  ├─ _docker_build   → hsync-wdos5-builder:{armv7,amd64}            (poetry install layer + sources)
  ├─ _run_pyinstaller_in_docker → build/wdos5/…/bin/hsync/          (--onedir bundle)
  └─ _wdos5_package_model       → build/wdos5/all/stage/<MODEL>/hsync/… → mksapkg-OS5 → dist/…bin
```

The staged version is validated by `compile.sh::_verify_embedded_version`:
the client `pyproject.toml` version must equal
`../hsync-common/hsync_common/constants.py::HSYNC_VERSION`, and the requested
version may only add a suffix. A `.bin` therefore cannot advertise a version
its engine does not report.

## CPU families

OS5 firmware exposes glibc up to 2.30, so the binary is compiled on Debian 10
(buster, glibc 2.28) for both families, regardless of the host distribution:

- ARMv7: `compile.sh::WDOS5_ARMV7_MODELS` (built under qemu-user, `linux/arm/v7`)
- amd64: `compile.sh::WDOS5_AMD64_MODELS` (`linux/amd64`)

One binary per family is shared by every model of that family.

## Runtime layout on the NAS

Paths are defined once in `packaging/Apkg/env`:

| Symbol | Purpose |
| --- | --- |
| `HSYNC_ROOT` | persistent data root on the data volume |
| `HSYNC_DATA_DIR` | default shared folder (`HSYNC_PATH` default) |
| `HSYNC_CONFIG_DIR`, `HSYNC_ENV_FILE` | configuration directory and `hsync.env` |
| `HSYNC_LOG_DIR`, `HSYNC_LOG_FILE` | log tree and the file the UI tails |
| `HSYNC_RUN_DIR`, `HSYNC_PID_FILE` | PID file written by `packaging/Apkg/start.sh` |
| `WEB_ROOT` | `/var/www/apps/<pkg>` symlink farm recreated at boot |

The installed program itself lives under `/shares/Volume_1/Nas_Prog/hsync`
(`packaging/Apkg/web/env_lib.php::HSYNC_PKG_DIR`), which is what the web UI
executes for trust probes and state resets.

## Build/packaging invariants

- The staged directory basename must equal the package name (`APP_NAME`):
  `mksapkg-OS5` tars its CWD name verbatim and OS5 rejects any other root.
  Guarded by `tests/test_packaging_contract.py::test_staged_tree_is_named_after_the_package`.
- `packaging/Apkg/apkg.rc` keeps the `__HSYNC_VERSION__` placeholder; only the
  staged copy is rendered, the source tree is never mutated.
- The declared icon (`packaging/Apkg/apkg.rc` `Icon: hsync.png`) is the committed
  `packaging/Apkg/web/hsync.png` (160x160), copied to the package root while
  staging. It is the shared HSYNC app icon — the master is
  `branding/hsync-app-icon.png` in the monorepo root (1024x1024), whose
  geometry mirrors the Android adaptive icon in `hsync-android`; regenerate
  the derivative by downscaling it with a high-quality filter, never by
  redrawing the mark.

  ```bash
  python3 -c "from PIL import Image; Image.open('branding/hsync-app-icon.png') \
    .resize((160, 160), Image.LANCZOS) \
    .save('packaging/Apkg/web/hsync.png', optimize=True)"
  ```
- `dist/`, `build/` and `packaging/.cache/` are never committed.
