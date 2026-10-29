"""Contract tests for the build pipeline and the Apkg tree.

These guard the parts that a code review cannot: the version really comes from
the sibling ``hsync-client``/``hsync-common`` checkouts, the staged directory is
named after the package (mksapkg-OS5 tars its CWD basename), and the icon the
package metadata declares is shipped.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPILE = ROOT / "compile.sh"
APKG = ROOT / "packaging" / "Apkg"
APKG_RC = APKG / "apkg.rc"
ICON = APKG / "web" / "hsync.png"

CLIENT_PYPROJECT = ROOT.parent / "hsync-client" / "pyproject.toml"
COMMON_CONSTANTS = ROOT.parent / "hsync-common" / "hsync_common" / "constants.py"

requires_siblings = pytest.mark.skipif(
    not CLIENT_PYPROJECT.is_file() or not COMMON_CONSTANTS.is_file(),
    reason="sibling hsync-client/hsync-common checkouts not present",
)


def _compile_text() -> str:
    return COMPILE.read_text(encoding="utf-8")


def _bash(snippet: str) -> subprocess.CompletedProcess[str]:
    """Run a snippet from the project root with compile.sh's helpers sourced."""
    return subprocess.run(
        ["bash", "-c", snippet],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_compile_sh_is_executable_and_parses() -> None:
    assert COMPILE.is_file()
    assert COMPILE.stat().st_mode & 0o111, "compile.sh must be executable"
    assert shutil.which("bash") is not None
    result = subprocess.run(
        ["bash", "-n", str(COMPILE)], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_compile_sh_exposes_the_uniform_option_surface() -> None:
    text = _compile_text()
    for flag in ("-c|--clean", "-t|--target", "-v|--version", "-h|--help"):
        assert flag in text, flag


def test_default_target_packages_every_model() -> None:
    """The default target is the multi-model build (there is no host artifact)."""
    assert 'local target="wd-os5-all"' in _compile_text()


def test_version_placeholder_is_injected_at_build_time() -> None:
    """apkg.rc carries the placeholder; compile.sh renders it and stamps VERSION."""
    assert "Version:\t__HSYNC_VERSION__" in APKG_RC.read_text(encoding="utf-8")
    text = _compile_text()
    assert "s/__HSYNC_VERSION__/${version}/g" in text
    assert 'echo "${version}" > "${stage_dir}/VERSION"' in text


def test_package_version_comes_from_the_siblings_not_this_repository() -> None:
    """The packaged version is the client version: this repo declares none."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "project" not in data, "pyproject.toml must not declare package metadata"
    assert "poetry" not in data.get("tool", {}), "pyproject.toml must stay tooling-only"
    text = _compile_text()
    assert '"${CLIENT_DIR}/pyproject.toml"' in text
    assert '"${COMMON_DIR}/hsync_common/constants.py"' in text


def test_staged_tree_is_named_after_the_package() -> None:
    """mksapkg-OS5 tars the CWD basename: it must equal APP_NAME or OS5 rejects the .bin."""
    text = _compile_text()
    assert 'local stage_dir="${stage_base}/${model}/${APP_NAME}"' in text


def test_declared_icon_is_shipped() -> None:
    """apkg.rc declares Icon: hsync.png and the source tree must provide it."""
    rc = APKG_RC.read_text(encoding="utf-8")
    assert re.search(r"^Icon:\s+hsync\.png$", rc, re.MULTILINE)
    assert ICON.is_file(), f"missing icon: {ICON}"
    assert 'cp -f "${WDOS5_SRC_APKG}/web/hsync.png" "${stage_dir}/hsync.png"' in _compile_text()


def test_every_model_is_assigned_to_one_cpu_family() -> None:
    text = _compile_text()
    block = text.split("readonly -a WDOS5_ARMV7_MODELS=", 1)[1].split("# Version override", 1)[0]
    armv7 = set(re.findall(r'"(MyCloud\w+|WD\w+|WDCloud)"', block.split("readonly -a")[0]))
    amd64_block = block.split("readonly -a WDOS5_AMD64_MODELS=(", 1)[1]
    amd64 = set(re.findall(r'"(MyCloud\w+|WD\w+|WDCloud)"', amd64_block))
    assert len(armv7) == 4, sorted(armv7)
    assert len(amd64) == 6, sorted(amd64)
    assert armv7 & amd64 == set()
    assert "MyCloudEX2Ultra" in armv7


def test_build_outputs_are_gitignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("/dist/", "/build/", "*.bin", "/packaging/.cache/"):
        assert pattern in ignore, pattern


@requires_siblings
def test_helpers_read_the_client_version() -> None:
    expected = re.search(
        r'^version\s*=\s*"([^"]+)"', CLIENT_PYPROJECT.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert expected is not None
    result = _bash("source ./compile.sh; get_version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected.group(1)


@requires_siblings
def test_engine_version_matches_the_client_checkout() -> None:
    result = _bash('source ./compile.sh; _verify_embedded_version "$(get_version)"')
    assert result.returncode == 0, result.stderr
    assert "Packaging hsync" in result.stdout


@requires_siblings
def test_unrelated_version_is_refused() -> None:
    """A base version other than the bundled engine must abort the build."""
    result = _bash("source ./compile.sh; _verify_embedded_version 999.0.0")
    assert result.returncode != 0
    assert "does not match the bundled engine" in result.stderr


@requires_siblings
def test_missing_bin_aborts_with_an_explicit_diagnostic(tmp_path: Path) -> None:
    """A silent mksapkg must surface the intended error, not a bare exit code.

    With ``set -e`` + ``pipefail`` an unmatched glob in the artifact lookup
    would abort the script (exit 2, no message) before the ``log_error`` below
    it could run; this pins the diagnostic.
    """
    binary = tmp_path / "hsync"
    binary.mkdir()
    (binary / "hsync").write_text("", encoding="utf-8")
    stage_base = tmp_path / "stage"
    out_dir = tmp_path / "out"
    stage_base.mkdir()
    out_dir.mkdir()

    result = _bash(
        "source ./compile.sh; _run_mksapkg() { :; }; "
        f"_wdos5_package_model MyCloudEX2Ultra {binary} 1.0.11 "
        f"{stage_base} {out_dir} /tmp/fake-mksapkg"
    )
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert "did not produce a .bin" in result.stderr


@requires_siblings
def test_malformed_bundle_fails_with_an_explicit_diagnostic(tmp_path: Path) -> None:
    """A bundle without the entry point must not surface as a bare chmod error."""
    binary = tmp_path / "hsync"
    binary.mkdir()
    result = _bash(f"source ./compile.sh; _install_binary {tmp_path / 'stage'} {binary}")
    assert result.returncode == 1
    assert "Frozen engine missing" in result.stderr


@requires_siblings
def test_suffix_on_the_engine_version_is_allowed() -> None:
    result = _bash(
        'source ./compile.sh; version="$(get_version)-alpha.1"; '
        '_verify_embedded_version "${version}"'
    )
    assert result.returncode == 0, result.stderr
