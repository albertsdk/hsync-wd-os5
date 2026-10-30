# Security Policy

## Supported Versions

Security fixes are applied to the latest released package on the `main` branch.

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅        |
| < 1.0   | ❌        |

The package version is the bundled client version; a `.bin` is only supported
while the matching client release is supported.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, use GitHub's private vulnerability reporting:

1. Open the **Security** tab of this repository.
2. Click **Report a vulnerability** to start a private advisory.

Please include the NAS model, firmware version, package version, steps to
reproduce, the impact, and any suggested mitigation. Allow a reasonable time for
a fix before any public disclosure.

## Security model

The package installs a service that runs **as root** on the NAS and is driven by
a web UI served by the stock Apache:

- **Config file** — `hsync.env` is root-owned with mode `0640` inside a `0750`
  directory. `start.sh` sources it as root, so `start.sh::env_file_is_root_safe`
  refuses to start when the file is not root-owned or is group/other-writable
  (that would be a local privilege-escalation path).
- **Secrets** — `HSYNC_API_KEY` and `HSYNC_P2P_PASSPHRASE` are exported to the
  daemon environment, never placed on its command line (they do not appear in
  `ps`). The web UI masks the shared password in the generated connect command.
- **Web endpoints** — every endpoint executes the packaged binary at a fixed
  absolute path with `escapeshellarg`-quoted arguments; no endpoint accepts a
  command or a target path from the caller. The log viewer reads one fixed file.
- **Transport** — server mode validates the TLS chain by default
  (`HSYNC_SERVER_TRUST=chain`); p2p is HTTPS/WSS-only with certificate
  fingerprint pinning. `HSYNC_INSECURE` disables verification and is for testing
  only.
- **Discovery servers** — authenticated by certificate fingerprint; a changed
  fingerprint is always refused.
- **Unattended appliance** — the NAS cannot answer an interactive `ask`
  prompt, so the shipped p2p default is `accept-new` (pin on first use). Pin
  the fingerprint out of band and switch to `strict` when the peers are known.

## Hardening recommendations

- Upload the HSYNC Server CA certificate (`Certificates` → **Upload…**) or pin
  the server fingerprint instead of using `HSYNC_INSECURE`.
- Pin the discovery server's fingerprint and use `HSYNC_RENDEZVOUS_SERVER_TRUST=strict`.
- Use a long shared password (`HSYNC_P2P_PASSPHRASE`, at least 12 characters;
  the installer generates 24) and keep it out of shell history and screenshots.
- Restrict dashboard access to administrators; the web UI has no separate login.
- Keep an independent backup of the synced share: this package deliberately
  never deletes local files (`HSYNC_DELETION_POLICY=keep`), but a peer can still
  overwrite them.
