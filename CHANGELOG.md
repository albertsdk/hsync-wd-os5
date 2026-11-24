# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Restore deleted files…** in Maintenance: lists the files the NAS deleted,
  restores one into the share (the next cycle propagates it) and empties the store
  after a confirmation. The endpoint runs `hsync trash`, so it needs no restart and
  cannot drift from the client's store format.
- A **Restore window** and a **Trash folder** field in *Sync Mode*, translated in
  every language the selector offers.
- Three checkboxes for the peer-mesh capabilities (serve blocks, fetch from peers,
  publish inventory), translated in every language the selector offers.

### Changed

- The launcher passes `--trash-retention` and exports `HSYNC_TRASH_DIR`; the
  config API whitelists and validates both keys, refusing a store inside the share.
- The launcher maps the three keys to the client flags, and the config
  API whitelists them.
- The web UI identity checks default to **Automatic**: the shipped `hsync.env`
  and launcher use `auto` (a CA chain when valid, else remember the first
  fingerprint), and a stored `chain` or `accept-new` is normalized to `auto`.
