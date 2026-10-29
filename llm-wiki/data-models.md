# Data models

This repository has no Python models. Its "data models" are the package
metadata, the on-disk layout constants and the single configuration store that
the UI, the launcher and the client share.

## Package metadata (`packaging/Apkg/apkg.rc`)

POSIX-shell-style key/value file consumed by `mksapkg-OS5` (tab-separated
`Key:\tValue`). Fields the build touches:

| Field | Owner | Note |
| --- | --- | --- |
| `Package` | `packaging/Apkg/apkg.rc` | must equal `compile.sh::APP_NAME` and the staged directory name |
| `Version` | `compile.sh::_stage_package_tree` | placeholder `__HSYNC_VERSION__`, rendered only in the staged copy |
| `Icon` | `packaging/Apkg/apkg.rc` | resolved from the package root: `_stage_package_tree` copies `web/hsync.png` there |
| `AddonIndexPage`, `AddonShowName`, `CenterType`, `UserControl` | `packaging/Apkg/apkg.rc` | dashboard integration (index page, label, app-grid placement) |
| `MinFWVer` | `packaging/Apkg/apkg.rc` | installability gate — never lower it for a prerelease |

## On-disk layout (`packaging/Apkg/env`)

`APKG_NAME`, `BINARY`, `HSYNC_ROOT`, `HSYNC_DATA_DIR`, `HSYNC_CONFIG_DIR`,
`HSYNC_LOG_DIR`, `HSYNC_RUN_DIR`, `HSYNC_ENV_FILE`, `HSYNC_LOG_FILE`,
`HSYNC_PID_FILE`, `WEB_ROOT`. The persistent tree lives on the data volume so it
survives package upgrades; the program lives under `Nas_Prog` and is replaced on
every install.

## Configuration model (`hsync.env`)

One flat key/value document, single-quoted on every line. Three views over the
same keys must stay aligned:

| View | Symbol |
| --- | --- |
| Form fields and defaults | `packaging/Apkg/web/index.html`, `packaging/Apkg/web/app.js::collectConfig` |
| Persistence + range validation | `packaging/Apkg/web/config_set.php::KEYS`, `::clamp_int` |
| Launch defaults + CLI translation | `packaging/Apkg/start.sh` (`: "${VAR:=…}"`, `set -- …`) |

Groups (see `../docs/configuration.md` for the user-facing reference):
mode/paths (`HSYNC_MODE`, `HSYNC_PATH`, `HSYNC_BUCKET`,
`HSYNC_SYNC_DIRECTION`, `HSYNC_FILTER_PATH`, `HSYNC_IGNORE_PATTERNS`), p2p
(`HSYNC_P2P_*`, `HSYNC_PREFER_MASTER`, `HSYNC_NEVER_MASTER`,
`HSYNC_ALLOW_DELETIONS`), discovery (`HSYNC_DISCOVERY_SERVER_*`, `HSYNC_MAP_DATA_PORT`,
`HSYNC_NTP_HOSTS`), server (`HSYNC_SERVER_URL`, `HSYNC_SERVER_*`, `HSYNC_API_KEY`,
`HSYNC_INSECURE`, `HSYNC_CA_CERT`), sync behaviour (`HSYNC_INTERVAL`,
`HSYNC_DELETION_POLICY`, `HSYNC_COMPRESSION_ENABLED`, `HSYNC_DELTA_*`,
`HSYNC_MAX_BW_*`, `HSYNC_MIN_FREE_DISK`, `HSYNC_MAX_INBOUND_SIZE_MB`,
`HSYNC_MASS_DELETE_*`), timing (`HSYNC_HTTP_TIMEOUT`,
`HSYNC_RECONNECT_DELAY`, `HSYNC_STABILITY_DELAY`, `HSYNC_MAX_WAIT_TIMEOUT`,
`HSYNC_TRANSFER_RETRY_*`) and performance/logging (`HSYNC_AUTOTUNE`,
`HSYNC_MAX_CONCURRENT_TRANSFERS`, `HSYNC_VERBOSE`, `HSYNC_QUIET`,
`HSYNC_DRY_RUN`).

Units are part of the model:

- delta floors are stored in **KB** and converted to bytes by `packaging/Apkg/start.sh`;
- `HSYNC_INTERVAL` is seconds, `0` = disabled;
- `HSYNC_MIN_FREE_DISK`/`HSYNC_MAX_BW_*` require an explicit unit (`500MB`),
  except `0` for "off";
- `HSYNC_PATH` must be absolute with no `..`; `HSYNC_FILTER_PATH` is relative.

Ownership/permissions are part of the contract too: `0640`, root-owned, inside a
`0750` directory — `packaging/Apkg/start.sh` refuses to source anything else.

## Trust store and sync state

Not modelled here: both are owned by the client (`hsync trust`,
`hsync state reset`) and only driven through `packaging/Apkg/web/trust.php` /
`packaging/Apkg/web/state_reset.php`.
The state directory is `HSYNC_STATE_DIR`, defaulted and exported by `packaging/Apkg/start.sh`.
