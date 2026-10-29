# Runtime module (`packaging/Apkg` lifecycle scripts)

The OS5 package manager invokes these hooks in the package directory
(`/shares/Volume_1/Nas_Prog/hsync`). Every script sources `packaging/Apkg/env`
for the on-disk constants; user settings live in `HSYNC_ENV_FILE`.

| Script | Role |
| --- | --- |
| `packaging/Apkg/preinst.sh` | stops a running daemon before the tree is replaced |
| `packaging/Apkg/install.sh` | merges the staged tree into the package path, normalises ownership/modes, links the web UI into `WEB_ROOT`, creates the persistent tree, seeds `hsync.env` |
| `packaging/Apkg/postinst.sh` | lifecycle symmetry hook (no config restore needed: config lives outside the package path) |
| `packaging/Apkg/init.sh` | re-creates the `WEB_ROOT` symlinks and fixes ownership at every boot |
| `packaging/Apkg/start.sh` | translates `hsync.env` into CLI flags + exported environment, launches the daemon under `nohup`, writes the PID file |
| `packaging/Apkg/stop.sh` | stops via the PID file, falls back to `pidof`, escalates to `SIGKILL` after a bounded wait |
| `packaging/Apkg/remove.sh` | stops the daemon, removes the package tree and `WEB_ROOT`; **keeps** the data tree |
| `packaging/Apkg/clean.sh` | removes only the `WEB_ROOT` symlinks (apache docroot refresh) |

## `packaging/Apkg/start.sh` — the env → CLI contract

- `packaging/Apkg/start.sh::env_file_is_root_safe` refuses to source a config
  that is not root-owned or is group/other-writable. `hsync.env` is sourced as
  root, so this is the local-privilege-escalation gate; it fails closed.
- Defaults are applied with `: "${VAR:=value}"`; they mirror the desktop client
  with one deliberate deviation: `HSYNC_DELETION_POLICY` defaults to `keep`
  (the NAS is a backup target).
- `packaging/Apkg/start.sh::is_uint` / `::is_uint_gt0` guard numeric flags, so a
  hand-edited value can never become a non-numeric argument; enum fields are
  re-validated with `case`.
- The subcommand is chosen from `HSYNC_MODE` (`p2p` | `server`) and always comes
  first; `--bucket` and `--path` are always passed.
- `server` mode aborts when `HSYNC_SERVER_URL` is empty.
- `HSYNC_PREFER_MASTER=true` only adds `--prefer-master` when the direction is
  `bidirectional` (the client rejects the combination).
- Delta floors are stored in KB (desktop unit) and converted to bytes when
  passed as `--delta-min-file-size*`.
- `HSYNC_INTERVAL=0` disables the periodic check by exporting `HSYNC_RESYNC=0`
  instead of passing a flag (the client has no CLI "off").
- Secrets (`HSYNC_API_KEY`, `HSYNC_P2P_PASSPHRASE`) and the env-only settings
  (bootnode/UPnP/NTP/server trust, per-file retry waits) are **exported**, never
  placed on the command line, so they cannot leak through `ps`.
- `HSYNC_STATE_DIR` defaults next to the config tree and is exported.

## Security invariants

- `hsync.env` is root-owned, mode `0640`, inside a `0750` directory
  (`packaging/Apkg/install.sh`, `packaging/Apkg/web/config_set.php`).
- The launcher refuses to start on an unsafe config file (see above).
- Web endpoints execute the packaged binary with absolute paths only:
  `packaging/Apkg/web/env_lib.php::HSYNC_BINARY`, `::hsync_run` (arguments are
  `escapeshellarg`-quoted), `::hsync_data_path` (absolute, no `..`),
  `::hsync_write_private` (temp file → rename, `0640`).
- The log endpoint reads a fixed path (no caller-selected file).

## Test coverage

`tests/test_wd_os5_web.py` asserts the launcher/installer invariants that are
easy to break by hand: `p2p` subcommand spelling, exported bootnode/UPnP
variables, no empty value passed to a numeric flag, the shipped defaults, and
the password wiring (`HSYNC_P2P_PASSPHRASE`, never `HSYNC_P2P_KEY`).
