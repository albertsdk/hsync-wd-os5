"""Regression tests for the WD OS5 web UI assets.

The web UI (PHP + vanilla JS under ``packaging/Apkg/web``) has no JS test
harness, so we guard the static assets with a small Python check. This catches
the bucket ``pattern`` regression where an unescaped ``-`` inside a character
class made the regex invalid under the JS ``v`` (unicodeSets) flag that modern
browsers apply to HTML ``pattern`` attributes (see commit history: ``37de4eb``
escaped the hyphen, ``fe37d97`` re-broke it).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PKG = PROJECT_ROOT / "packaging" / "Apkg"
WEB = PKG / "web"
I18N = WEB / "i18n"
APP_JS = WEB / "app.js"
INDEX_HTML = WEB / "index.html"

# Endpoints that are actually executed (not just inspected) need the PHP CLI;
# the static assertions do not.
requires_php = pytest.mark.skipif(shutil.which("php") is None, reason="php CLI not available")

# Expected, v-flag-safe bucket pattern. The hyphen is escaped (``\-``) so the
# inner character class compiles under both the ``u`` and ``v`` flags; this
# mirrors the authoritative server-side grammar in config_set.php.
EXPECTED_BUCKET_PATTERN = r"^[A-Za-z0-9]([A-Za-z0-9_\-]*[A-Za-z0-9])?$"

_BUCKET_PATTERN_RE = re.compile(
    r'<input[^>]*\bid="HSYNC_BUCKET"[^>]*\bpattern="([^"]*)"', re.DOTALL
)


def test_bucket_pattern_is_v_flag_safe() -> None:
    """The bucket input pattern must escape the hyphen (valid under the v flag)."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = _BUCKET_PATTERN_RE.search(html)
    assert match is not None, "HSYNC_BUCKET input with a pattern= not found in index.html"
    pattern = match.group(1)
    assert pattern == EXPECTED_BUCKET_PATTERN, (
        f"bucket pattern is {pattern!r}, expected {EXPECTED_BUCKET_PATTERN!r} "
        "(unescaped '-' in a character class is invalid under the JS v flag)"
    )


# ── placeholder styling ──────────────────────────────────────────────────

_HEX_RE = re.compile(r"#([0-9A-Fa-f]{6})")


def _relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance of an ``#rrggbb`` colour."""
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]

    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg: str, bg: str) -> float:
    lf, lb = _relative_luminance(fg), _relative_luminance(bg)
    hi, lo = max(lf, lb), min(lf, lb)
    return (hi + 0.05) / (lo + 0.05)


def test_placeholder_text_is_visually_distinct_and_accessible() -> None:
    """Placeholders are hints, not saved values: they must not share the input
    text colour (#161D1D) and must keep WCAG AA contrast on the white field, or
    an empty field reads as a filled one."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = re.search(r"#hsync-app\s+input::placeholder\s*\{([^}]*)\}", html)
    assert match is not None, "no '#hsync-app input::placeholder' rule in index.html"
    color = _HEX_RE.search(match.group(1))
    assert color is not None, "the ::placeholder rule sets no colour"
    value = color.group(0).upper()
    assert value != "#161D1D", "placeholder colour equals the input text colour"
    assert _contrast_ratio(value, "#FFFFFF") >= 4.5, (
        f"placeholder {value} is below the WCAG AA 4.5:1 contrast on white"
    )


# ── rendezvous / mode consistency ────────────────────────────────────────
_SUPPORTED_RE = re.compile(r"const SUPPORTED = \[([^\]]*)\]")


def _supported_locales() -> list[str]:
    """Read the language list from app.js so the tests track the single source."""
    match = _SUPPORTED_RE.search(APP_JS.read_text(encoding="utf-8"))
    assert match is not None, "SUPPORTED not found in app.js"
    return re.findall(r"'([^']+)'", match.group(1))


def test_rendezvous_server_fields_present_in_ui() -> None:
    """The p2p section exposes the rendezvous-server list and the UPnP toggle."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="HSYNC_RENDEZVOUS_SERVER_ENDPOINTS"' in html
    assert 'id="HSYNC_MAP_DATA_PORT"' in html


def test_php_config_whitelists_rendezvous_server_keys() -> None:
    """Both PHP endpoints whitelist the renamed environment keys."""
    for name in ("config_get.php", "config_set.php"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert "HSYNC_RENDEZVOUS_SERVER_ENDPOINTS" in text, name
        assert "HSYNC_MAP_DATA_PORT" in text, name


def test_i18n_has_rendezvous_keys_in_all_locales() -> None:
    import json

    for locale in _supported_locales():
        data = json.loads((I18N / f"{locale}.json").read_text(encoding="utf-8"))
        assert data.get("field.rendezvous_server"), locale
        assert data.get("field.upnp"), locale


def test_start_sh_uses_p2p_subcommand_and_exports_rendezvous() -> None:
    start = (PKG / "start.sh").read_text(encoding="utf-8")
    assert 'SUBCOMMAND="p2p"' in start
    assert 'SUBCOMMAND="lan"' not in start
    assert "export HSYNC_RENDEZVOUS_SERVER_ENDPOINTS" in start
    assert "export HSYNC_MAP_DATA_PORT" in start


def test_mode_value_is_p2p_everywhere() -> None:
    """The mode value ``lan`` is retired: UI, validation and service agree on p2p."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert '<option value="p2p"' in html
    assert '<option value="lan"' not in html
    php = (WEB / "config_set.php").read_text(encoding="utf-8")
    assert "['p2p', 'server']" in php
    start = (PKG / "start.sh").read_text(encoding="utf-8")
    assert "p2p)    SUBCOMMAND=" in start


def test_config_set_accepts_endpoint_grammar() -> None:
    """``config_set.php`` validates the HOST[:PORT] grammar, not a bare hostname."""
    php = (WEB / "config_set.php").read_text(encoding="utf-8")
    assert "$endpoint_re" in php
    assert r"\[" in php  # bracketed IPv6 literal in the endpoint regex


def test_config_set_whitelists_server() -> None:
    """``config_set.php`` validates ``HSYNC_SERVER_URL`` (bare host or https:// URL)."""
    php = (WEB / "config_set.php").read_text(encoding="utf-8")
    assert "case 'HSYNC_SERVER_URL':" in php


def test_server_input_is_text_not_url() -> None:
    """A bare ``HOST[:PORT]`` must be accepted by the browser (type=url blocks it)."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert (
        'id="HSYNC_SERVER_URL" type="text"' in html or 'type="text" name="HSYNC_SERVER_URL"' in html
    )
    assert 'type="url" name="HSYNC_SERVER_URL"' not in html


def test_i18n_has_server_field_in_all_locales() -> None:
    import json

    for locale in _supported_locales():
        data = json.loads((I18N / f"{locale}.json").read_text(encoding="utf-8"))
        assert data.get("field.server"), locale


def test_rendezvous_ports_field_is_wired_end_to_end() -> None:
    """``HSYNC_RENDEZVOUS_SERVER_EXTRA_PORTS`` is exposed, whitelisted, validated and exported."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="HSYNC_RENDEZVOUS_SERVER_EXTRA_PORTS"' in html

    for name in ("config_get.php", "config_set.php"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert "HSYNC_RENDEZVOUS_SERVER_EXTRA_PORTS" in text, name

    php = (WEB / "config_set.php").read_text(encoding="utf-8")
    assert "case 'HSYNC_RENDEZVOUS_SERVER_EXTRA_PORTS':" in php

    start = (PKG / "start.sh").read_text(encoding="utf-8")
    assert "export HSYNC_RENDEZVOUS_SERVER_EXTRA_PORTS" in start

    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "'HSYNC_RENDEZVOUS_SERVER_EXTRA_PORTS'" in app  # CONNECT_FIELDS + generated env prefix

    import json

    for locale in _supported_locales():
        data = json.loads((I18N / f"{locale}.json").read_text(encoding="utf-8"))
        assert data.get("field.rendezvous_server_extra_ports"), locale


def test_rendezvous_transport_field_is_wired_end_to_end() -> None:
    """``HSYNC_RENDEZVOUS_TRANSPORT`` is exposed, whitelisted, validated, exported."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="HSYNC_RENDEZVOUS_TRANSPORT"' in html
    assert 'option value="auto"' in html
    assert 'option value="tcp"' in html

    for name in ("config_get.php", "config_set.php"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert "HSYNC_RENDEZVOUS_TRANSPORT" in text, name

    php = (WEB / "config_set.php").read_text(encoding="utf-8")
    assert "case 'HSYNC_RENDEZVOUS_TRANSPORT':" in php
    assert "['auto', 'quic', 'tcp']" in php

    start = (PKG / "start.sh").read_text(encoding="utf-8")
    assert "HSYNC_RENDEZVOUS_TRANSPORT:=auto" in start
    assert "export HSYNC_RENDEZVOUS_TRANSPORT" in start
    assert "auto|quic|tcp" in start

    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "'HSYNC_RENDEZVOUS_TRANSPORT'" in app  # CONNECT_FIELDS + generated env prefix

    import json

    for locale in _supported_locales():
        data = json.loads((I18N / f"{locale}.json").read_text(encoding="utf-8"))
        assert data.get("field.rendezvous_transport"), locale
        assert data.get("transport_option.auto"), locale
        assert data.get("transport_option.tcp"), locale


def test_i18n_dictionaries_cover_every_supported_locale() -> None:
    """Every language in app.js SUPPORTED has a complete i18n dictionary.

    Guards against adding a language to the selector without shipping its
    translations (the UI would fall back to the English ``data-i18n`` defaults)
    and against a dictionary drifting from the English key set.
    """
    import json

    locales = _supported_locales()
    assert locales, "app.js exposes no supported languages"
    assert "en" in locales, "English must remain a supported language"

    reference = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
    assert reference, "en.json is empty"

    for locale in locales:
        path = I18N / f"{locale}.json"
        assert path.exists(), f"missing i18n dictionary for {locale!r}"
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(set(reference) - set(data))
        extra = sorted(set(data) - set(reference))
        assert not missing and not extra, (
            f"{locale}.json keys differ from en.json: missing={missing} extra={extra}"
        )
        empty = [
            key for key, value in data.items() if not isinstance(value, str) or not value.strip()
        ]
        assert not empty, f"{locale}.json has empty values: {empty}"


def test_language_selector_has_native_names_for_every_locale() -> None:
    """The selector shows the desktop-style native names, one per language."""
    app = APP_JS.read_text(encoding="utf-8")
    match = re.search(r"const LANGUAGE_NAMES = \{(.*?)\n    \};", app, re.DOTALL)
    assert match is not None, "LANGUAGE_NAMES not found in app.js"
    names = dict(re.findall(r"(\w+):\s*'([^']*)'", match.group(1)))
    for locale in _supported_locales():
        assert names.get(locale), f"missing native name for {locale!r}"


# ── desktop parity: keys, labels, defaults ─────────────────────────────
def _form_names() -> set[str]:
    html = INDEX_HTML.read_text(encoding="utf-8")
    return set(re.findall(r'name="(HSYNC_[A-Z0-9_]+)"', html))


def _php_keys(name: str) -> set[str]:
    text = (WEB / name).read_text(encoding="utf-8")
    block = text.split("const KEYS = [", 1)[1].split("];", 1)[0]
    return set(re.findall(r"'(HSYNC_[A-Z0-9_]+)'", block))


def test_php_whitelists_match_the_form() -> None:
    """config_get.php, config_set.php and the form expose the same key set.

    The per-file retry waits are the only keys kept in the whitelist without a
    form field: the desktop does not expose them either, and keeping them means
    a hand-edited value survives a save.
    """
    get_keys = _php_keys("config_get.php")
    set_keys = _php_keys("config_set.php")
    form = _form_names()
    assert get_keys == set_keys
    assert form <= get_keys, sorted(form - get_keys)
    assert get_keys - form == {
        "HSYNC_TRANSFER_RETRY_MIN_WAIT",
        "HSYNC_TRANSFER_RETRY_MAX_WAIT",
    }, sorted(get_keys - form)


def test_every_boolean_key_is_normalized() -> None:
    """Every boolean the server validates is a checkbox the UI collects."""
    app = APP_JS.read_text(encoding="utf-8")
    block = re.search(r"const CHECKBOX_KEYS = \[(.*?)\];", app, re.DOTALL)
    assert block is not None, "CHECKBOX_KEYS not found in app.js"
    checkboxes = set(re.findall(r"'(HSYNC_[A-Z0-9_]+)'", block.group(1)))

    php = (WEB / "config_set.php").read_text(encoding="utf-8")
    tail = php.split("case 'HSYNC_PREFER_MASTER':", 1)[1]
    tail = tail.split("if (!in_array($val, ['true', 'false'], true))", 1)[0]
    booleans = {"HSYNC_PREFER_MASTER"} | set(re.findall(r"case '(HSYNC_[A-Z0-9_]+)':", tail))
    assert checkboxes == booleans, (sorted(checkboxes - booleans), sorted(booleans - checkboxes))


def test_inline_labels_match_the_dictionary() -> None:
    """The English fallback inside index.html must equal en.json, key by key."""
    import html as html_mod
    import json

    data = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
    src = INDEX_HTML.read_text(encoding="utf-8")
    mismatches = {}
    for key, text in re.findall(r'data-i18n="([^"]+)"[^>]*>([^<]*)<', src):
        inline = html_mod.unescape(text).strip()
        if inline and data.get(key) != inline:
            mismatches[key] = (inline, data.get(key))
    assert not mismatches, mismatches


def test_no_numeric_flag_receives_an_empty_value() -> None:
    """The launcher guards every numeric flag and disables the resync explicitly."""
    start = (PKG / "start.sh").read_text(encoding="utf-8")
    for var in (
        "HSYNC_PEER_RENDEZVOUS_TIMEOUT",
        "HSYNC_HTTP_TIMEOUT",
        "HSYNC_RECONNECT_DELAY",
        "HSYNC_STABILITY_DELAY",
        "HSYNC_MAX_WAIT_TIMEOUT",
        "HSYNC_MAX_INBOUND_SIZE_MB",
    ):
        assert f'is_uint "${{{var}}}"' in start or f'is_uint_gt0 "${{{var}}}"' in start, var
    assert "export HSYNC_RESYNC=0" in start


def test_defaults_match_the_desktop_reference() -> None:
    """The shipped NAS defaults equal hsync-desktop's (see hsync_desktop/config.py)."""
    install = (PKG / "install.sh").read_text(encoding="utf-8")
    start = (PKG / "start.sh").read_text(encoding="utf-8")
    expected = {
        "HSYNC_BUCKET": "my-bucket",
        "HSYNC_P2P_GROUP": "my-group",
        "HSYNC_PEER_RENDEZVOUS_TIMEOUT": "10",
        "HSYNC_MAP_DATA_PORT": "true",
        "HSYNC_MDNS": "true",
        "HSYNC_HTTP_TIMEOUT": "30",
        "HSYNC_RECONNECT_DELAY": "5",
        "HSYNC_STABILITY_DELAY": "5",
        "HSYNC_MAX_WAIT_TIMEOUT": "120",
        "HSYNC_MIN_FREE_DISK": "500MB",
        "HSYNC_MAX_INBOUND_SIZE_MB": "10240",
        "HSYNC_DELTA_MIN_FILE_SIZE": "256",
        "HSYNC_DELTA_MIN_FILE_SIZE_P2P": "1024",
        "HSYNC_SERVER_TRUST": "auto",
        "HSYNC_RENDEZVOUS_SERVER_TRUST": "auto",
        "HSYNC_COMPRESSION_ENABLED": "true",
        "HSYNC_PREFER_MASTER": "false",
        "HSYNC_NEVER_MASTER": "false",
        "HSYNC_AUTOTUNE": "true",
        "HSYNC_MASS_DELETE_GUARD": "true",
        "HSYNC_MASS_DELETE_THRESHOLD": "50",
        "HSYNC_MASS_DELETE_PERCENT": "50",
        "HSYNC_MAX_CONCURRENT_TRANSFERS": "0",
        # Deliberate NAS deviation: this device is a backup target.
        "HSYNC_DELETION_POLICY": "keep",
    }
    for key, value in expected.items():
        assert f'{key}="{value}"' in install, f"install.sh seed for {key}"
        assert f': "${{{key}:={value}}}"' in start, f"start.sh fallback for {key}"


@requires_php
def test_config_set_clamps_ranges(tmp_path: Path) -> None:
    """A behavioural check: out-of-range and empty values become valid ones."""
    env_file = tmp_path / "hsync.env"
    prepend = tmp_path / "prepend.php"
    prepend.write_text(
        "<?php\n"
        f"define('HSYNC_ENV', '{env_file}');\n"
        f"define('HSYNC_CONFIG', '{tmp_path}');\n"
        "$_SERVER['REQUEST_METHOD'] = 'POST';\n"
        "$_SERVER['CONTENT_TYPE'] = 'application/x-www-form-urlencoded';\n"
        "$_POST = [\n"
        "    'HSYNC_MODE' => 'p2p',\n"
        "    'HSYNC_BUCKET' => 'bad bucket',\n"
        "    'HSYNC_HTTP_TIMEOUT' => '',\n"
        "    'HSYNC_PEER_RENDEZVOUS_TIMEOUT' => '999',\n"
        "    'HSYNC_RECONNECT_DELAY' => '0',\n"
        "    'HSYNC_P2P_PEER_READ_CAP' => '100',\n"
        "    'HSYNC_SYNC_DIRECTION' => 'sideways',\n"
        "    'HSYNC_COMPRESSION_ENABLED' => 'true',\n"
        "    'HSYNC_INTERVAL' => '5',\n"
        "    'HSYNC_MASS_DELETE_PERCENT' => '250',\n"
        "    'HSYNC_P2P_GROUP' => \"grp\\nHSYNC_VERBOSE\",\n"
        "];\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "php",
            "-d",
            f"auto_prepend_file={prepend}",
            "-d",
            "display_errors=0",
            str(WEB / "config_set.php"),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    written = dict(re.findall(r"^(HSYNC_[A-Z0-9_]+)='([^']*)'$", env_file.read_text(), re.M))
    assert written["HSYNC_BUCKET"] == "my-bucket"
    assert written["HSYNC_HTTP_TIMEOUT"] == "30"
    assert written["HSYNC_PEER_RENDEZVOUS_TIMEOUT"] == "60"
    assert written["HSYNC_RECONNECT_DELAY"] == "1"
    assert written["HSYNC_P2P_PEER_READ_CAP"] == "32"
    assert written["HSYNC_SYNC_DIRECTION"] == "bidirectional"
    assert written["HSYNC_INTERVAL"] == "20"
    assert written["HSYNC_MASS_DELETE_PERCENT"] == "100"

    # A newline in a free-text field must not break the line-based .env file.
    lines = [ln for ln in env_file.read_text().splitlines() if ln and not ln.startswith("#")]
    assert all(re.fullmatch(r"HSYNC_[A-Z0-9_]+='.*'", ln) for ln in lines), lines
    group_line = next(ln for ln in lines if ln.startswith("HSYNC_P2P_GROUP="))
    assert "HSYNC_VERBOSE" in group_line and group_line.count("=") == 1


# ── shared password (desktop parity) ───────────────────────────────────
def test_p2p_password_is_wired_end_to_end() -> None:
    """The NAS manages HSYNC_P2P_PASSPHRASE (12+), not a 32-char raw key."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = re.search(r'<input[^>]*id="HSYNC_P2P_PASSPHRASE"[^>]*minlength="(\d+)"', html)
    assert match is not None, "HSYNC_P2P_PASSPHRASE input not found"
    assert int(match.group(1)) == 12
    assert 'name="HSYNC_P2P_PASSPHRASE"' in html
    assert 'name="HSYNC_P2P_KEY"' not in html

    for name in ("config_get.php", "config_set.php"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert "HSYNC_P2P_PASSPHRASE" in text, name
        assert "HSYNC_P2P_KEY" not in text, name

    start = (PKG / "start.sh").read_text(encoding="utf-8")
    assert "export HSYNC_P2P_PASSPHRASE" in start
    assert "HSYNC_P2P_KEY" not in start

    install = (PKG / "install.sh").read_text(encoding="utf-8")
    assert 'HSYNC_P2P_PASSPHRASE="${P2P_PASSPHRASE}"' in install
    assert "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789" in install
    assert "HSYNC_P2P_KEY" not in install

    app = APP_JS.read_text(encoding="utf-8")
    assert "'HSYNC_P2P_PASSPHRASE'" in app
    assert "HSYNC_P2P_KEY" not in app

    env_lib = (WEB / "env_lib.php").read_text(encoding="utf-8")
    assert "HSYNC_P2P_PASSPHRASE" in env_lib
    assert "HSYNC_P2P_KEY" not in env_lib

    import json

    for locale in _supported_locales():
        data = json.loads((I18N / f"{locale}.json").read_text(encoding="utf-8"))
        assert data.get("field.p2p_password"), locale
        assert data.get("note.p2p_password"), locale
        assert data.get("toast.password_too_short"), locale
        assert "field.p2p_key" not in data, locale


@requires_php
def test_config_set_enforces_the_password_floor(tmp_path: Path) -> None:
    """An 11-char password is dropped; a 12-char one is persisted."""
    for value, expected in (("abcdefghijk", ""), ("abcdwxyz1234", "abcdwxyz1234")):
        env_file = tmp_path / "hsync.env"
        prepend = tmp_path / "prepend.php"
        prepend.write_text(
            "<?php\n"
            f"define('HSYNC_ENV', '{env_file}');\n"
            f"define('HSYNC_CONFIG', '{tmp_path}');\n"
            "$_SERVER['REQUEST_METHOD'] = 'POST';\n"
            "$_SERVER['CONTENT_TYPE'] = 'application/x-www-form-urlencoded';\n"
            "$_POST = ['HSYNC_MODE' => 'p2p', 'HSYNC_P2P_PASSPHRASE' => " + repr(value) + "];\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "php",
                "-d",
                f"auto_prepend_file={prepend}",
                "-d",
                "display_errors=0",
                str(WEB / "config_set.php"),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        written = dict(re.findall(r"^(HSYNC_[A-Z0-9_]+)='([^']*)'$", env_file.read_text(), re.M))
        assert written["HSYNC_P2P_PASSPHRASE"] == expected
        assert "HSYNC_P2P_KEY" not in written


# ── the local trash (ADR-0056, ADR 007) ────────────────────────────────
@requires_php
def test_config_set_validates_the_trash_keys(tmp_path: Path) -> None:
    """The store must stay outside the share and the window inside its range."""
    env_file = tmp_path / "hsync.env"
    prepend = tmp_path / "prepend.php"
    prepend.write_text(
        "<?php\n"
        f"define('HSYNC_ENV', '{env_file}');\n"
        f"define('HSYNC_CONFIG', '{tmp_path}');\n"
        "$_SERVER['REQUEST_METHOD'] = 'POST';\n"
        "$_SERVER['CONTENT_TYPE'] = 'application/x-www-form-urlencoded';\n"
        "$_POST = [\n"
        "    'HSYNC_PATH' => '/mnt/HD/HD_a2/hsync/data',\n"
        "    'HSYNC_TRASH_DIR' => '/mnt/HD/HD_a2/hsync/data/trash',\n"
        "    'HSYNC_TRASH_RETENTION_DAYS' => '99999',\n"
        "];\n",
        encoding="utf-8",
    )

    def run() -> dict[str, str]:
        subprocess.run(
            [
                "php",
                "-d",
                f"auto_prepend_file={prepend}",
                "-d",
                "display_errors=0",
                str(WEB / "config_set.php"),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        return dict(re.findall(r"^(HSYNC_[A-Z0-9_]+)='([^']*)'$", env_file.read_text(), re.M))

    written = run()
    # A store inside the share would be synced to every device.
    assert written["HSYNC_TRASH_DIR"] == ""
    assert written["HSYNC_TRASH_RETENTION_DAYS"] == "3650"

    # A sibling path on the same volume is where the default lives: kept.
    prepend.write_text(
        prepend.read_text().replace("/mnt/HD/HD_a2/hsync/data/trash", "/mnt/HD/HD_a2/hsync/trash"),
        encoding="utf-8",
    )
    assert run()["HSYNC_TRASH_DIR"] == "/mnt/HD/HD_a2/hsync/trash"

    # Traversal and an empty window fall back to the shipped defaults.
    prepend.write_text(
        prepend.read_text()
        .replace("/mnt/HD/HD_a2/hsync/trash", "../../etc")
        .replace("'99999'", "''"),
        encoding="utf-8",
    )
    written = run()
    assert written["HSYNC_TRASH_DIR"] == ""
    assert written["HSYNC_TRASH_RETENTION_DAYS"] == "30"


@requires_php
def test_config_set_validates_the_trash_budget(tmp_path: Path) -> None:
    """The budget is stored in bytes (the client's unit) and clamped."""
    env_file = tmp_path / "hsync.env"
    prepend = tmp_path / "prepend.php"

    def run(value: str) -> str:
        prepend.write_text(
            "<?php\n"
            f"define('HSYNC_ENV', '{env_file}');\n"
            f"define('HSYNC_CONFIG', '{tmp_path}');\n"
            "$_SERVER['REQUEST_METHOD'] = 'POST';\n"
            "$_SERVER['CONTENT_TYPE'] = 'application/x-www-form-urlencoded';\n"
            "$_POST = [\n"
            "    'HSYNC_PATH' => '/mnt/HD/HD_a2/hsync/data',\n"
            f"    'HSYNC_TRASH_MAX_SIZE' => '{value}',\n"
            "];\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "php",
                "-d",
                f"auto_prepend_file={prepend}",
                "-d",
                "display_errors=0",
                str(WEB / "config_set.php"),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        written = dict(re.findall(r"^(HSYNC_[A-Z0-9_]+)='([^']*)'$", env_file.read_text(), re.M))
        return written["HSYNC_TRASH_MAX_SIZE"]

    assert run("2147483648") == "2147483648"  # 2 GiB, the unit the client reads
    assert run("0") == "0"  # auto: the client derives it from the filesystem
    assert run("not-a-number") == "0"  # dropped instead of aborting the startup
    assert run("2199023255552") == "1099511627776"  # clamped to the form's 1 TiB


@requires_php
def test_trash_endpoint_gates_every_request(tmp_path: Path) -> None:
    """trash.php loads, refuses a GET and reports a missing share."""
    prepend = tmp_path / "prepend.php"
    prepend.write_text(
        "<?php\n$_SERVER['REQUEST_METHOD'] = 'GET';\n",
        encoding="utf-8",
    )

    def run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "php",
                "-d",
                f"auto_prepend_file={prepend}",
                "-d",
                "display_errors=0",
                str(WEB / "trash.php"),
            ],
            text=True,
            capture_output=True,
            check=True,
        )

    assert "method_not_allowed" in run().stdout

    # A POST on a host without the share (this machine) hits the folder guard
    # instead of running the client: the endpoint never guesses a path.
    prepend.write_text(
        "<?php\n"
        "$_SERVER['REQUEST_METHOD'] = 'POST';\n"
        "$_SERVER['CONTENT_TYPE'] = 'application/x-www-form-urlencoded';\n"
        "$_POST = ['action' => 'list'];\n",
        encoding="utf-8",
    )
    result = run()
    assert "missing_folder" in result.stdout
    assert "Fatal error" not in result.stdout + result.stderr


def test_trash_endpoint_is_a_thin_wrapper_over_the_client_verbs() -> None:
    """trash.php relays `hsync trash` instead of parsing the store's layout."""
    php = (WEB / "trash.php").read_text(encoding="utf-8")
    assert "hsync_require_post(" in php
    for action in ("list", "restore", "empty"):
        assert f"case '{action}':" in php, action
    for verb in ("'trash', 'list'", "'trash', 'restore'", "'trash', 'empty'"):
        assert verb in php, verb
    # The listing is the client's JSON contract; argv quoting belongs to hsync_run.
    assert "--json" in php
    assert "escapeshellarg" not in php
    # The restore carries the folder's direction: a download-only folder must be
    # refused by the client instead of looping delete/recreate.
    assert "HSYNC_SYNC_DIRECTION" in php


def test_trash_controls_are_wired_in_the_ui() -> None:
    """The maintenance button, the dialog and its rows exist and are bound."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    for element in (
        "hsync-btn-trash",
        "hsync-trash-modal",
        "hsync-trash-list",
        "hsync-trash-empty",
        "hsync-trash-close",
    ):
        assert f'id="{element}"' in html, element

    app = APP_JS.read_text(encoding="utf-8")
    assert "trash.php" in app
    for call in ("action: 'list'", "action: 'restore'", "action: 'empty'"):
        assert call in app, call
    assert "bind('hsync-btn-trash'" in app
    # Emptying is destructive and must ask first.
    assert "confirm.empty_trash" in app


def test_trash_keys_are_translated_in_all_locales() -> None:
    """The trash strings follow the same all-locales rule as the rest."""
    import json

    keys = {
        "field.trash_retention",
        "field.trash_dir",
        "field.trash_max_size",
        "tip.trash_max_size",
        "note.trash",
        "action.trash",
        "trash.title",
        "trash.empty_all",
        "trash.empty",
        "trash.restore",
        "trash.cross_volume",
        "toast.trash_ok",
        "toast.trash_error",
        "confirm.empty_trash",
    }
    for locale in _supported_locales():
        data = json.loads((I18N / f"{locale}.json").read_text(encoding="utf-8"))
        missing = sorted(key for key in keys if not str(data.get(key, "")).strip())
        assert not missing, (locale, missing)


def test_trash_settings_reach_the_launcher() -> None:
    """Every key is whitelisted, editable and translated into the launch."""
    trash_keys = {"HSYNC_TRASH_DIR", "HSYNC_TRASH_RETENTION_DAYS", "HSYNC_TRASH_MAX_SIZE"}
    for name in ("config_get.php", "config_set.php"):
        assert trash_keys <= _php_keys(name), name
    assert trash_keys <= _form_names()

    start = (PKG / "start.sh").read_text(encoding="utf-8")
    assert 'is_uint "${HSYNC_TRASH_RETENTION_DAYS}"' in start
    assert '--trash-retention "${HSYNC_TRASH_RETENTION_DAYS}"' in start
    # Empty means "the client's default", never an empty assignment.
    assert '[ -n "${HSYNC_TRASH_DIR}" ] && export HSYNC_TRASH_DIR' in start
    # The budget is the client's key (bytes); 0/empty leaves it to the client.
    assert 'is_uint "${HSYNC_TRASH_MAX_SIZE}"' in start
    assert "export HSYNC_TRASH_MAX_SIZE" in start


def test_trash_budget_is_edited_in_gb() -> None:
    """The form edits whole GB; one conversion site maps it to the stored bytes."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "const BYTES_PER_GB_FIELDS = ['HSYNC_TRASH_MAX_SIZE']" in app
    assert app.count("BYTES_PER_GB_FIELDS.forEach") == 2, "apply and collect must both convert"
    assert 'name="HSYNC_TRASH_MAX_SIZE"' in html
    assert 'max="1024"' in html


def test_trash_store_is_addressed_with_the_daemons_environment() -> None:
    """The endpoint must not read a different store than the daemon writes."""
    lib = (WEB / "env_lib.php").read_text(encoding="utf-8")
    assert "function hsync_trash_root(" in lib
    assert "function hsync_same_volume(" in lib
    assert "HSYNC_TRASH_DIR=" in lib, "hsync_run must export the store location"
