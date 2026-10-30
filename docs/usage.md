# Use the web UI

The HSYNC page is served by the NAS dashboard. Everything below happens in the
browser, as the dashboard administrator.

## Open the page

In the My Cloud dashboard, open **Apps** and click the **HSYNC** icon. The
header shows the service state and a language selector; the footer shows the
version of the installed engine.

| Badge | Meaning |
| --- | --- |
| **running** | The daemon is up and syncing (or waiting for peers) |
| **stopped** | Installed but not started — press **Start** |
| **unknown** | The service state could not be read; try **Restart**, then check **View log** |

## Choose a mode

The **Mode** section switches the whole form between the two run modes:

- **p2p** — this NAS is a peer. Fill **Mode & Group** (share name and shared
  password), optionally **Finding devices** (discovery servers for cross-network
  rendezvous) and **Role & security**.
- **server** — this NAS is a client of a central HSYNC Server. Fill **Server**
  (URL and API key) and, if you use a private CA or a pinned certificate,
  **Certificates**.

Fields that belong to the other mode are hidden and are not sent to the device.

## First configuration

1. Pick the mode.
2. Set the **shared folder** (`HSYNC_PATH`, default `/mnt/HD/HD_a2/hsync/data`)
   and the **share name** (`HSYNC_BUCKET`).
3. In p2p mode, set the **shared password** (`HSYNC_P2P_PASSPHRASE`, at least
   12 characters). Use the same share name and password on every device of the
   group.
4. Review **Sync Mode**, **Timing & Intervals**, **Performance** and
   **Deletion protection** — the defaults suit a NAS backup target.
5. Press **Save**, then **Start**.

Every field is documented in [configuration.md](configuration.md).

## Connect another device

The **Connect another device** section prints the `hsync` command to run on a
second device so it joins the same group. It is built from the values currently
in the form, updates while you type, and is rebuilt from the saved
configuration after **Save**. In server mode the section explains that the other
device must be pointed at the same server instead.

The password is masked in the command; **Show password** reveals it and
**Copy** copies the unmasked command to the clipboard.

## Control the service

| Button | Effect |
| --- | --- |
| **Save** | Validates the form and writes `hsync.env` atomically |
| **Start** | Starts the daemon with the saved configuration |
| **Stop** | Stops the daemon; synced files are untouched |
| **Restart** | Stop followed by start — use it after changing the network or trust settings |
| **View log** | Opens the live log overlay |

Saving does not restart a running daemon. Press **Restart** when a change must
take effect immediately.

## View the log

**View log** tails `/mnt/HD/HD_a2/hsync/log/hsync.log` in near real time. The
overlay offers **Auto-scroll** (on by default), **Clear** (clears the view, not
the file) and **Close**. Polling stops when the overlay is closed.

## Ignore rules

**Ignore rules…** edits `<shared folder>/.hsyncignore`, the same gitignore-style
file the client reads. The client reloads it while running, so a saved rule set
applies to the next file event without a restart.

Any file listed there is not transferred. The **Ignore patterns** field in the
form adds comma-separated patterns on top of the file.

## Trusted servers & devices

**Manage trusted servers & devices…** edits the trust store used for
fingerprint pinning:

- **Discovery servers** — the `rdv/1` node identity
- **Server** — the central HSYNC Server certificate
- **Peer** — a p2p master certificate

For each kind the dialog lists the pinned fingerprints and lets you **Add**
(host + `sha256:…` fingerprint) or **Remove** an entry. **Test rendezvous
server** and **Test Connection** contact the configured endpoint and show its
fingerprint, so you can pin it before the first connection.

## Reset sync state

**Reset sync state…** stops the service, quarantines the local sync state and
starts the service again. Use it when the NAS and its peers disagree about what
is already synced (for example after restoring a share from a backup).

The quarantined state is kept next to the live one, so the operation can be
undone by an operator with shell access.

## Clear all settings

There is no "factory reset" button. To start from the shipped defaults, edit
`/mnt/HD/HD_a2/hsync/config/hsync.env` with shell access or reinstall the
package after deleting that file.
