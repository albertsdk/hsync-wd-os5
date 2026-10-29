# HSYNC for WD My Cloud OS5

This documentation covers the **HSYNC app package for WD My Cloud OS5**: what it
installs, how to put it on the NAS, and how to operate it from the dashboard web
UI.

HSYNC keeps a folder on the NAS in sync with your other devices. The NAS can be
a **peer** (p2p mode) or a **client of a central HSYNC Server** (server mode);
either way all sync traffic is plain HTTP/HTTPS, so it works through corporate
proxies and firewalls.

> [!WARNING]
> HSYNC creates, overwrites, moves, and deletes files. Keep verified,
> independent backups. The NAS ships with deletion **disabled**
> (`HSYNC_DELETION_POLICY=keep`), so removals made on other devices are not
> applied here.

## Requirements

- A supported WD My Cloud OS5 device (see the model table in the
  [README](../README.md)) on firmware **5.27.100 or later**
- Access to the My Cloud dashboard as an administrator
- Somewhere to keep your own backup of the synced data

## Where to go next

| I want to… | Read |
| --- | --- |
| Install the package for the first time | [installation.md](installation.md) |
| Learn the web UI and get the first sync running | [usage.md](usage.md) |
| Look up a field, its default and its allowed values | [configuration.md](configuration.md) |
| Fix a problem (install rejected, no peers, TLS errors) | [troubleshooting.md](troubleshooting.md) |

The HSYNC client itself — CLI flags, server mode, p2p internals — is documented
in the [client repository](https://github.com/albertsdk/hsync-client).
