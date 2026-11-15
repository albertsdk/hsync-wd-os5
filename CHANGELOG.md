# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- The web UI identity checks default to **Automatic**: the shipped `hsync.env`
  and launcher use `auto` (a CA chain when valid, else remember the first
  fingerprint), and a stored `chain` or `accept-new` is normalized to `auto`.
