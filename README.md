# HSYNC — WD My Cloud OS5 package

**HSYNC** keeps folders in sync between devices. This repository builds the
**WD My Cloud OS5 app package** (`.bin`): it installs the HSYNC client on the NAS
as a background service and serves a small web UI, from the stock dashboard,
to configure and control it without SSH.

> [!WARNING]
> HSYNC creates, overwrites, moves, and deletes files. Keep verified,
> independent backups. The software is provided "as is", without warranty of
> any kind — see [LICENSE](LICENSE).

## What you get

| Item | Description |
| --- | --- |
| Background service | The HSYNC client (the platform-specific frozen binary) runs as a NAS service and syncs the configured shared folder |
| Web UI | Configuration, start/stop/restart, log viewer, ignore list, trust store, sync-state reset, "connect another device" command |
| Data on the NAS | Everything lives under `/mnt/HD/HD_a2/hsync` (`config/`, `data/`, `log/`, `run/`, `state/`) and survives package upgrades |
| Modes | **p2p** (NAS is a peer; optionally found across networks through a discovery server) and **server** (NAS is a client of a central HSYNC Server) |

The NAS is treated as a **backup target** by default: deletions made on the
other devices are never applied here (`HSYNC_DELETION_POLICY=keep`), so a
mistake on a source host cannot empty the NAS share.

## Supported devices

| CPU family | Models |
| --- | --- |
| ARMv7 (`armhf`) | My Cloud EX2 Ultra, My Cloud Mirror, My Cloud, WD Cloud |
| amd64 | My Cloud EX2100, EX4100, DL2100, DL4100, PR2100, PR4100 |

Firmware **My Cloud OS 5, version 5.27.100 or later** is required (the value the
package declares in `packaging/Apkg/apkg.rc`). Python is **not** required on the
NAS: the service ships as a self-contained binary.

## Install

Prerequisites: a supported My Cloud OS5 device with its stock dashboard.

1. Download the `.bin` for your model from the
   [Releases page](https://github.com/albertsdk/hsync-wd-os5/releases).
2. Open the NAS dashboard, go to **Apps**, and upload the file with
   **Install an App manually**.
3. Open the **HSYNC** app icon to reach the web UI.

Step-by-step instructions, including what to do when the package manager
rejects a file: [docs/installation.md](docs/installation.md).

## First configuration

After the install, open the app and pick a mode:

- **p2p** — the NAS and the other devices find each other on the local network.
  Set the same share name (`HSYNC_BUCKET`) and shared password
  (`HSYNC_P2P_PASSPHRASE`) everywhere; the **Connect another device** section
  prints the command to run on the other machines.
- **server** — point the NAS at an HSYNC Server with
  `HSYNC_SERVER_URL` + `HSYNC_API_KEY`.

Then press **Save** and **Start**. The web UI tour is in
[docs/usage.md](docs/usage.md); every field is described in
[docs/configuration.md](docs/configuration.md).

## Documentation

| Guide | Content |
| --- | --- |
| [docs/installation.md](docs/installation.md) | Dashboard install, upgrade, uninstall, what stays on disk |
| [docs/usage.md](docs/usage.md) | Web UI: modes, service controls, log viewer, ignore list, trust store, reset |
| [docs/configuration.md](docs/configuration.md) | Every `HSYNC_*` key: meaning, default, allowed range |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Symptom → cause → fix |

The HSYNC client itself (CLI, server mode, p2p internals) is documented in the
[client repository](https://github.com/albertsdk/hsync-client).

## Development

Building a `.bin` requires Docker with qemu-user-static and the sibling
`hsync-client` + `hsync-common` checkouts. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

BSD-3-Clause — see [LICENSE](LICENSE).
