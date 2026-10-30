# Web UI module (`packaging/Apkg/web`)

PHP + vanilla JS served by the stock Apache under `WEB_ROOT`
(`packaging/Apkg/env::WEB_ROOT`, a symlink farm of `packaging/Apkg/web/*`).
It configures and controls the daemon without SSH. The reference for defaults
and wording is `hsync-desktop` (`../hsync-desktop/hsync_desktop/config.py`); NAS-only additions
are the explicit pin/TOFU fields and the dangerous opt-ins that the desktop
handles with dialogs.

## Files

| File | Role |
| --- | --- |
| `packaging/Apkg/web/index.html` | markup + scoped CSS; every selector rooted at `#hsync-app` |
| `packaging/Apkg/web/app.js` | controller: load/persist config, service control, log viewer, ignore editor, trust manager, probes, i18n, connect-command generator |
| `packaging/Apkg/web/env_lib.php` | runtime paths, POSIX `.env` parser, shared-folder resolver, binary runner, JSON reply, atomic private write |
| `packaging/Apkg/web/config_get.php` | returns the whitelisted `HSYNC_*` keys from `hsync.env` as JSON |
| `packaging/Apkg/web/config_set.php` | validates + writes the whitelisted keys atomically (`::clamp_int`, per-key grammars) |
| `packaging/Apkg/web/hsyncignore_get.php` / `_set.php` | read/replace `<HSYNC_PATH>/.hsyncignore` (hot-reloaded by the client) |
| `packaging/Apkg/web/trust.php` | `hsync trust <kind> list\|add\|remove` for rendezvous/server/peer |
| `packaging/Apkg/web/state_reset.php` | stop → `hsync state reset --folder … --quarantine --json` → start |
| `packaging/Apkg/web/test.php` | reachability + fingerprint via `hsync trust <kind> fingerprint` |
| `packaging/Apkg/web/ca_cert_upload.php` | stores a PEM as `config/ca.pem` (the `HSYNC_CA_CERT` path) |
| `packaging/Apkg/web/service.php` | start/stop/restart/status of the daemon |
| `packaging/Apkg/web/log_get.php` | incremental tail of `hsync.log` (fixed path, capped chunks) |
| `packaging/Apkg/web/i18n/<code>.json` | dictionary; `packaging/Apkg/web/app.js::t` falls back to the key name |

## Config flow

`packaging/Apkg/web/config_get.php` → `packaging/Apkg/web/app.js::applyConfig` →
form fields → `packaging/Apkg/web/app.js::collectConfig` →
`packaging/Apkg/web/config_set.php`. The daemon is launched by
`packaging/Apkg/start.sh`, which
translates `hsync.env` into CLI flags (see [runtime.md](runtime.md)).

`packaging/Apkg/web/config_set.php` always writes the **whole** whitelisted key set, so a key
without a form field is reset to its default on Save.

## Invariants

- `packaging/Apkg/web/config_get.php`, `packaging/Apkg/web/config_set.php` and the form share one key set
  (`tests/test_wd_os5_web.py::test_php_whitelists_match_the_form`); only the
  per-file retry waits are whitelisted without a field.
- Every numeric field is clamped to the range the engine accepts
  (`packaging/Apkg/web/config_set.php::clamp_int`), so a saved file is always launchable.
- Every boolean the server normalises is a checkbox the UI collects
  (`test_every_boolean_key_is_normalized`).
- The English dictionary equals the inline `data-i18n` fallback text
  (`test_inline_labels_match_the_dictionary`), and every locale in
  `packaging/Apkg/web/app.js::SUPPORTED` carries the same keys.
- `packaging/Apkg/start.sh` never passes an empty argument to a numeric flag and disables the
  periodic check explicitly with `HSYNC_RESYNC=0`.

## "Connect another device" command generator

`packaging/Apkg/web/app.js::renderConnectCommand` builds the `hsync` command to run on a second
device joining the group coordinated by the NAS. It is shown in a readonly
`#hsync-connect-command` textarea (not `<code>`: the WD dashboard/remotewd
injector can strip or hide `code` contents), recomputed live from the form
fields on delegated `input`/`change`/`keyup` events (so it survives dashboard
node replacement) and on mode switches (`packaging/Apkg/web/app.js::syncModeVisibility`). After a
successful Save it is rebuilt from the persisted configuration, so it always
reflects what `hsync.env` contains.

Scope: **p2p mode only**; in server mode the section shows an explanatory note.
Only connection-matching fields are emitted — per-device behaviour and the role
are omitted because election resolves them. The shared password is rendered
masked with a reveal toggle; **Copy** copies the unmasked command via
`navigator.clipboard` with an `execCommand` fallback. Every interpolated value
is POSIX single-quoted by `packaging/Apkg/web/app.js::shellQuote`.

## Human docs

`../../docs/usage.md` (UI tour) and `../../docs/configuration.md` (key reference).
Domain rule: any CLI flag / `HSYNC_*` / i18n change requires the synchronized
update described in the root `AGENTS.md`.
