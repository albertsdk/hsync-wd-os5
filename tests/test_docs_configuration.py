"""Keep the configuration reference honest against the code that enforces it.

`docs/configuration.md` is the user-facing reference for every `HSYNC_*` key.
The ranges it documents are enforced by `packaging/Apkg/web/config_set.php`
(`clamp_int`), so a change there without a docs change would leave operators
with a wrong reference: this test fails in that case.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_SET = ROOT / "packaging" / "Apkg" / "web" / "config_set.php"
REFERENCE = ROOT / "docs" / "configuration.md"

_CASE_RE = re.compile(r"^\s*case '(HSYNC_[A-Z0-9_]+)':")
_CLAMP_RE = re.compile(
    r"clamp_int\(\s*\$val,\s*(\d+),\s*(\d+),\s*(.+?)\)\s*;",
    re.DOTALL,
)


def _clamped_ranges() -> dict[str, tuple[int, int, int | None]]:
    """Map each clamped key to (min, max, fallback) from config_set.php."""
    lines = CONFIG_SET.read_text(encoding="utf-8").splitlines()
    ranges: dict[str, tuple[int, int, int | None]] = {}
    pending: list[str] = []
    in_case_run = False

    index = 0
    while index < len(lines):
        line = lines[index]
        case = _CASE_RE.match(line)
        if case:
            # Consecutive `case` lines share one body (e.g. the two delta
            # floors); a new run after other statements is a different key.
            if not in_case_run:
                pending = []
            pending.append(case.group(1))
            in_case_run = True
            index += 1
            continue
        if "clamp_int(" in line and pending:
            # The call may span several lines (the delta floors use a ternary
            # fallback), so match against the following block.
            block = "\n".join(lines[index : index + 8])
            call = _CLAMP_RE.search(block)
            assert call is not None, pending
            fallback_raw = call.group(3).strip()
            fallback = int(fallback_raw) if fallback_raw.isdigit() else None
            for key in pending:
                ranges[key] = (int(call.group(1)), int(call.group(2)), fallback)
            pending = []
        in_case_run = False
        index += 1
    return ranges


def _documented_rows() -> dict[str, tuple[str, str]]:
    """Map each documented key to (default cell, allowed cell)."""
    rows: dict[str, tuple[str, str]] = {}
    for line in REFERENCE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `HSYNC_"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        rows[cells[0].strip("`")] = (cells[1], cells[2])
    return rows


def test_every_documented_key_is_whitelisted() -> None:
    """A documented key that the web UI cannot persist is a dead instruction."""
    php = CONFIG_SET.read_text(encoding="utf-8")
    block = php.split("const KEYS = [", 1)[1].split("];", 1)[0]
    whitelisted = set(re.findall(r"'(HSYNC_[A-Z0-9_]+)'", block))
    documented = set(_documented_rows())
    assert documented, "no HSYNC_* rows found in docs/configuration.md"
    assert documented <= whitelisted, sorted(documented - whitelisted)


def test_documented_ranges_match_the_clamping_code() -> None:
    """Every clamped key documents the same default, minimum and maximum."""
    rows = _documented_rows()
    problems: list[str] = []

    for key, (minimum, maximum, fallback) in sorted(_clamped_ranges().items()):
        row = rows.get(key)
        if row is None:
            problems.append(f"{key}: missing from docs/configuration.md")
            continue
        default_cell, allowed_cell = row

        if fallback is not None and default_cell.strip("`") != str(fallback):
            problems.append(
                f"{key}: docs default {default_cell!r} != config_set fallback {fallback}"
            )
        for label, value in (("min", minimum), ("max", maximum)):
            if not re.search(rf"(?<![\d.]){value}(?![\d.])", allowed_cell):
                problems.append(
                    f"{key}: docs do not mention the {label} {value} ({allowed_cell!r})"
                )

    assert not problems, "\n".join(problems)
