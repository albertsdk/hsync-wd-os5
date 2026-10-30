# Troubleshooting

Start with **View log** in the web UI: the daemon writes everything to
`/mnt/HD/HD_a2/hsync/log/hsync.log`, and the first lines of a failed start say
exactly which check refused to run.

## The dashboard refuses the package

**Symptom** — during **Install an App manually** the dashboard reports
`Failed to load the app package for installation`.

**Cause** — the file is not a valid OS5 package or it was built for another
model family. The CPU family must match the device.

**Fix** — download the `.bin` whose name starts with your model from the
[Releases page](https://github.com/albertsdk/hsync-wd-os5/releases) and do not
rename it. If you build the package yourself, verify that the version override
is numeric (a prerelease suffix such as `-alpha.1` may be rejected) and rebuild
with `./compile.sh -v 1.2.0`.

## The badge stays "stopped" or "unknown"

**Check** — press **Start**, wait a few seconds, then **View log**.

Typical causes in the log:

| Log line | Cause | Fix |
| --- | --- | --- |
| `REFUSING to source unsafe …hsync.env` | The config file is not root-owned or is group/other-writable | `chown 0:0` and `chmod 0640` the file; the UI writes it correctly |
| `hsync executable missing or not executable` | The installed tree lost its permissions | Reinstall the package |
| a configuration error from the client | A value the UI would have clamped was written by hand | Open the UI and press **Save** to rewrite the file with valid values |

## No peers are found (p2p)

1. Confirm both devices use the same share name (`HSYNC_BUCKET`) and the same
   password (`HSYNC_P2P_PASSPHRASE`).
2. If the devices are on **different networks**, set `HSYNC_RENDEZVOUS_SERVER_ENDPOINTS` to the
   rendezvous server and make sure the NAS can reach it (**Test rendezvous
   server**).
3. Check that the local firewall/UPnP allows the master port; set
   `HSYNC_P2P_PORT` to an explicit port if the router needs a fixed mapping.
4. Increase `HSYNC_PEER_RENDEZVOUS_TIMEOUT` if the network is slow (range 5–60 s).

## TLS or fingerprint errors

| Message | Meaning | Fix |
| --- | --- | --- |
| `unknown server` / fingerprint mismatch | The certificate changed or the pin is wrong | **Manage trusted servers & devices**, remove the stale entry, **Test Connection** and pin the new fingerprint |
| `untrusted rendezvous server` | No pin and no TOFU/accept-new policy | Set `HSYNC_RENDEZVOUS_SERVER_TRUST` or pin the fingerprint |
| `certificate verify failed` (server mode) | The CA is not trusted | Upload the CA PEM in **Certificates**, or pin the fingerprint |

Never use `HSYNC_INSECURE` to "make it work": it disables the identity check
instead of fixing it.

## A sync cycle pauses with a mass-delete warning

The guard stopped a cycle that would delete more than
`HSYNC_MASS_DELETE_THRESHOLD` / `HSYNC_MASS_DELETE_PERCENT` of the local files.
That is usually correct — a peer arriving with an empty or wrong share. Verify
the share name and the peer's data, then adjust the thresholds only if the
deletion is genuinely intended.

## Files keep re-syncing, or the NAS and a peer disagree

Use **Reset sync state…**. The service stops, the local state is quarantined
and the daemon starts again: the next cycle rebuilds it from the actual content
instead of trusting the old history.

## The disk is full

The transfer stops when free space would drop below `HSYNC_MIN_FREE_DISK`
(default `500MB`). Free space, or lower the threshold, or send the share to a
larger folder by changing `HSYNC_PATH`.

## The web UI shows "—" as version

The page reads the version from the installed binary. If it stays empty, the
service cannot execute the binary: reinstall the package and check the log for
`hsync executable missing`.
