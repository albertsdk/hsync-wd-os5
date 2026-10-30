# Configuration reference

All settings live in one POSIX `.env` file:

```text
/mnt/HD/HD_a2/hsync/config/hsync.env
```

The web UI is the normal way to read and write it; an administrator can also
edit it over SSH. **Save** in the web UI rewrites the whole file atomically, so
a key that has no field in the form is reset to its shipped default.

Format rules enforced by the web UI:

- one `KEY='value'` per line, single-quoted, values escaped for POSIX shells;
- the file is root-owned with mode `0640` because the service sources it as
  root at start — a file writable by a local NAS user would be a privilege
  escalation path, and the launcher refuses to start in that case;
- values that span lines are collapsed, numeric fields are clamped into the
  range below, and unknown values fall back to the default.

`hsync.env` is the NAS-side view: the launcher translates these keys into the
client's flags and environment variables. The client-side meaning of a key (and
the flags it maps to) is documented in the
[client repository](https://github.com/albertsdk/hsync-client); the tables below
describe what the NAS writes and what the range check accepts.

## General

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_MODE` | `p2p` | `p2p`, `server` |
| `HSYNC_PATH` | `/mnt/HD/HD_a2/hsync/data` | absolute path without `..` |
| `HSYNC_BUCKET` | `my-bucket` | letters, digits, `_`, `-`; must start and end alphanumeric |
| `HSYNC_SYNC_DIRECTION` | `bidirectional` | `bidirectional`, `upload-only`, `download-only` |
| `HSYNC_FILTER_PATH` | empty | path relative to the shared folder; empty syncs everything |
| `HSYNC_IGNORE_PATTERNS` | empty | comma-separated gitignore-style patterns (at most 50) |

## p2p mode

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_P2P_GROUP` | `my-group` | free text, identical on every device |
| `HSYNC_P2P_PASSPHRASE` | random 24 characters at install time | at least 12 characters; empty disables authenticated p2p writes |
| `HSYNC_P2P_PORT` | `0` | `0` (auto-assign) or `1`–`65535` |
| `HSYNC_PREFER_MASTER` | `false` | `true`, `false` |
| `HSYNC_NEVER_MASTER` | `false` | `true`, `false` |
| `HSYNC_P2P_TRUST` | `accept-new` | `accept-new` (pin on first use), `strict` (pin out of band first) |
| `HSYNC_P2P_PEER_DOWNLOAD` | `true` | `true`, `false` — allow peer-assisted reads |
| `HSYNC_P2P_PEER_READ_CAP` | `2` | `1`–`32` — simultaneous peer reads |
| `HSYNC_P2P_PEER_SOURCES_MAX` | `3` | `1`–`8` — peers a file may be fetched from |
| `HSYNC_P2P_ALLOW_UNAUTHENTICATED_WRITES` | `false` | `true`, `false` — dangerous |
| `HSYNC_P2P_ALLOW_UNAUTHENTICATED` | `false` | `true`, `false` — dangerous |
| `HSYNC_ALLOW_DELETIONS` | `false` | `true`, `false` |
| `HSYNC_PEER_RENDEZVOUS_TIMEOUT` | `10` | `5`–`60` seconds |

## Discovery servers (p2p across networks)

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_RENDEZVOUS_SERVER_ENDPOINTS` | empty | `HOST`, `HOST:PORT`, `[IPv6]`, `[IPv6]:PORT`; empty keeps rendezvous on the local network |
| `HSYNC_RENDEZVOUS_SERVER_EXTRA_PORTS` | empty | comma-separated UDP ports `1`–`65535`, order preserved |
| `HSYNC_RENDEZVOUS_SERVER_FINGERPRINTS` | empty | up to two `sha256:<64 hex>` (or bare hex) pins, comma-separated |
| `HSYNC_RENDEZVOUS_SERVER_TOFU` | `false` | `true`, `false` — trust the discovery server on first use |
| `HSYNC_RENDEZVOUS_SERVER_TRUST` | `ask` | `ask`, `accept-new`, `strict`, `none` |
| `HSYNC_MAP_DATA_PORT` | `true` | `true`, `false` — map the master port with UPnP |
| `HSYNC_NTP_HOSTS` | empty | comma-separated SNTP hosts used for clock-offset correction |

An empty pin fails closed: without `HSYNC_RENDEZVOUS_SERVER_TOFU` or
`accept-new`/`none` the discovery server is not trusted automatically.

## Server mode

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_SERVER_URL` | empty | `HOST`, `HOST:PORT` or an `https://` URL |
| `HSYNC_API_KEY` | empty | the API key issued by the server |
| `HSYNC_INSECURE` | `false` | `true`, `false` — skip certificate validation (insecure) |
| `HSYNC_CA_CERT` | empty | absolute path to a readable PEM file (upload it from the UI) |
| `HSYNC_SERVER_TRUST` | `chain` | `chain` (CA validation), `ask`, `accept-new`, `strict`, `none` |
| `HSYNC_SERVER_FINGERPRINTS` | empty | up to two `sha256:<64 hex>` pins |
| `HSYNC_SERVER_TOFU` | `false` | `true`, `false` |

`HSYNC_INSECURE` is mutually exclusive with a pin or TOFU; prefer uploading the
CA certificate or pinning the fingerprint.

## Sync behaviour

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_INTERVAL` | `0` | `0` disables the periodic full check; otherwise `20`–`3600` seconds |
| `HSYNC_DELETION_POLICY` | `keep` | `keep` (never delete locally), `propagate` |
| `HSYNC_COMPRESSION_ENABLED` | `true` | `true`, `false` |
| `HSYNC_DELTA_ENABLED` | `true` | `true`, `false` — block-level delta transfer |
| `HSYNC_DELTA_MIN_FILE_SIZE` | `256` | `0`–`1048576` KB |
| `HSYNC_DELTA_MIN_FILE_SIZE_P2P` | `1024` | `0`–`1048576` KB |
| `HSYNC_MAX_BW_UPLOAD` | empty | empty (unlimited) or a size with a unit (`500KB`, `2MB`, `1.5GB`) |
| `HSYNC_MAX_BW_DOWNLOAD` | empty | empty (unlimited) or a size with a unit |
| `HSYNC_MIN_FREE_DISK` | `500MB` | a size with a unit, or `0` to disable the check |
| `HSYNC_MAX_INBOUND_SIZE_MB` | `10240` | `0`–`10000000` MB (`0` = no limit) |
| `HSYNC_MASS_DELETE_GUARD` | `true` | `true`, `false` |
| `HSYNC_MASS_DELETE_THRESHOLD` | `50` | `0`–`100000` files |
| `HSYNC_MASS_DELETE_PERCENT` | `50` | `0`–`100` percent |

The mass-delete guard pauses a cycle that would remove more than the threshold
(or percent) of the local files, and is the second safety net behind
`HSYNC_DELETION_POLICY=keep`.

## Timing

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_HTTP_TIMEOUT` | `30` | `1`–`300` seconds |
| `HSYNC_RECONNECT_DELAY` | `5` | `1`–`60` seconds |
| `HSYNC_STABILITY_DELAY` | `5` | `1`–`60` seconds |
| `HSYNC_MAX_WAIT_TIMEOUT` | `120` | `10`–`3600` seconds |
| `HSYNC_TRANSFER_RETRY_MIN_WAIT` | empty | seconds, decimals allowed; empty uses the engine default |
| `HSYNC_TRANSFER_RETRY_MAX_WAIT` | empty | seconds, decimals allowed; empty uses the engine default |

## Performance

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_AUTOTUNE` | `true` | `true`, `false` — adapt timeout, retry and concurrency |
| `HSYNC_MAX_CONCURRENT_TRANSFERS` | `0` | `0` (auto) or `1`–`20` |

## Logging

| Key | Default | Allowed values |
| --- | --- | --- |
| `HSYNC_VERBOSE` | `false` | `true`, `false` |
| `HSYNC_QUIET` | `false` | `true`, `false` |
| `HSYNC_DRY_RUN` | `false` | `true`, `false` — log what would happen without transferring |

The log file is `/mnt/HD/HD_a2/hsync/log/hsync.log`; **View log** in the web UI
tails it.
