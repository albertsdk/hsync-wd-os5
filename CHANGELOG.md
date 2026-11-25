# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The trash dialog states what the store holds against its size limit (*Store: 120
  MB of 4 GB, 8 files*), from one `hsync trash stats` call; the limit is shared,
  so the figures cover every share.
- A row whose stored copy is gone is marked (*no stored copy*) and has no Restore
  button, so the modal never offers a command that can only fail.
- A **Restore all** button in the trash dialog: one client call puts every entry
  back and reports how many returned and how many stayed.

- The page warns when a trash setting changed while the service runs: those keys
  are read at start, so the save shows "restart the service to apply" instead of
  leaving the UI and the daemon on different stores.

- **Restore deleted files…** in Maintenance: lists the files the NAS deleted,
  restores one into the share (the next cycle propagates it) and empties the store
  after a confirmation. The endpoint runs `hsync trash`, so it needs no restart and
  cannot drift from the client's store format.
- A **Restore window** and a **Trash folder** field in *Sync Mode*, translated in
  every language the selector offers.
- Three checkboxes for the peer-mesh capabilities (serve blocks, fetch from peers,
  publish inventory), translated in every language the selector offers.

### Changed

- The launcher passes `--trash-retention`, exports `HSYNC_TRASH_DIR` and
  `HSYNC_TRASH_MAX_SIZE`; the config API whitelists and validates the three keys,
  refusing a store inside the share.
- The trash size limit (GB) is editable in the web UI like the restore window:
  the form edits whole GB, the stored key is the client's byte count.
- The launcher maps the three keys to the client flags, and the config
  API whitelists them.
- The web UI identity checks default to **Automatic**: the shipped `hsync.env`
  and launcher use `auto` (a CA chain when valid, else remember the first
  fingerprint), and a stored `chain` or `accept-new` is normalized to `auto`.
