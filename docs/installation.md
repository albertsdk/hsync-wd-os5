# Install the package on your NAS

This page is the dashboard procedure for a first install. For what each field
means afterwards, see [usage.md](usage.md) and [configuration.md](configuration.md).

## Prerequisites

- A supported My Cloud OS5 device on firmware 5.27.100 or later
- The `.bin` file for **your** model (the CPU family must match: ARMv7 models
  and amd64 models use different binaries)
- Dashboard administrator access

## 1. Download the package

Open the [Releases page](https://github.com/albertsdk/hsync-wd-os5/releases) and
download `<MODEL>_hsync_<version>.bin` for your device.

The file name starts with the model the build targets, for example
`MyCloudEX2Ultra_hsync_1.2.3.bin`. A package for a different model has the wrong
CPU family and is refused by the device.

## 2. Install from the dashboard

1. Sign in to the My Cloud dashboard.
2. Open **Apps**.
3. Use **Install an App manually** and select the `.bin` file you downloaded.
4. Confirm the install and wait for the dashboard to finish.

The package manager unpacks the service under
`/shares/Volume_1/Nas_Prog/hsync`, links the web UI under
`/var/www/apps/hsync`, and starts the service once.

## 3. Open the web UI

The **HSYNC** icon appears in the Apps grid. Open it: the page shows the current
service state and the configuration form.

The shipped configuration is a working p2p profile (share `my-bucket`, group
`my-group`, a random shared password), so the service starts and waits for
peers. Follow [usage.md](usage.md) to match it with your other devices.

## 4. Verify that it is running

The status badge next to the page title reads **running** when the daemon is
up. If it reads **stopped** or **unknown** right after the install, check the log
with **View log** and see [troubleshooting.md](troubleshooting.md).

## Upgrade

Install the newer `.bin` the same way. The package manager runs the lifecycle
hooks: the user configuration (`hsync.env`) is backed up before the upgrade and
restored afterwards, and the data under `/mnt/HD/HD_a2/hsync` is preserved.

## Uninstall

Remove the app from **Apps** in the dashboard. The package keeps the persistent
data tree: configuration, synced files, log and sync state are **not** deleted,
so a reinstall resumes where it left off.

To start over completely, delete `/mnt/HD/HD_a2/hsync` manually after the
uninstall.

## What lives on the NAS

| Path | Content |
| --- | --- |
| `/shares/Volume_1/Nas_Prog/hsync` | Installed service: binary (`bin/hsync/`), lifecycle scripts and web UI |
| `/var/www/apps/hsync` | Symlinks to the web UI assets (recreated at every boot) |
| `/mnt/HD/HD_a2/hsync/config/hsync.env` | Your configuration, root-owned and not group/other-writable |
| `/mnt/HD/HD_a2/hsync/data` | Default shared folder |
| `/mnt/HD/HD_a2/hsync/log/hsync.log` | Service log |
| `/mnt/HD/HD_a2/hsync/run/hsync.pid` | PID of the running daemon |
| `/mnt/HD/HD_a2/hsync/state` | Sync state (causal history, tombstones) |

The data tree is on the data volume on purpose: it survives package upgrades
and a full reinstall.
