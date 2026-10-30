# Support

## How to get help

- **[Documentation](docs/README.md)** — install, web UI tour, configuration
  reference and troubleshooting.
- **[Troubleshooting](docs/troubleshooting.md)** — install rejected, service not
  starting, no peers found, TLS/fingerprint errors, mass-delete guard.
- **[GitHub Issues](https://github.com/albertsdk/hsync-wd-os5/issues)** — bug
  reports and feature requests. Please search existing issues first.
- **[GitHub Discussions](https://github.com/albertsdk/hsync-wd-os5/discussions)** —
  questions and general discussion.
- **[Security Policy](SECURITY.md)** — how to report vulnerabilities privately.
- **[HSYNC client](https://github.com/albertsdk/hsync-client)** — the engine's
  CLI, server mode and p2p internals.

## Before asking for help

1. Open **View log** in the web UI: the first lines of a failed start say which
   check refused to run.
2. Confirm the package matches the device (ARMv7 vs amd64 models use different
   binaries) and that the firmware is supported.
3. Check the shared-folder path, free space (`HSYNC_MIN_FREE_DISK`) and the
   share name / password match on every device.
4. For TLS problems, use **Test rendezvous server** / **Test Connection** and
   compare the fingerprint with the one you pinned.

## 💚 Solo project

HSYNC is a passion project maintained in spare time by volunteers. Feature
requests, bug reports, and pull requests are reviewed as soon as possible, but
response times may vary. Thank you for your patience and support!
