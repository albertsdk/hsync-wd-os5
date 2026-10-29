#!/usr/bin/env bash
#
# HSYNC — WD My Cloud OS5 packaging build script
#
# Fetches the hsync client from the sibling ``../hsync-client`` checkout (with
# its own ``../hsync-common`` path dependency), freezes it with PyInstaller
# inside a Debian 10 (buster, glibc 2.28) container for each CPU family the NAS
# firmware supports, and packs the result plus the ``packaging/Apkg`` tree into
# a ``.bin`` installer with mksapkg-OS5.
#
# The client is consumed as *sources* (the same sibling-build contract
# hsync-desktop uses): there is no Poetry dependency on it and no import of its
# internals outside the frozen engine.
#
# Usage:
#   ./compile.sh [options]
#
# Options:
#   -c, --clean             Clean build artifacts before building
#   -t, --target TARGET     Build target (default: wd-os5-all)
#                           Supported:
#                               wd-os5-all           Every supported WD OS5 model
#                                                    (ARMv7 + amd64, 10 .bin)
#                               wd-ex2-ultra-os5     My Cloud EX2 Ultra only
#                                                    (ARMv7 single .bin)
#   -v, --version VERSION   Override the packaged version (default: the
#                           hsync-client version). Also settable via the
#                           HSYNC_VERSION environment variable. A suffix
#                           (e.g. 1.2.0-alpha.1) is carried verbatim into
#                           apkg.rc, VERSION and the .bin file name.
#   -h, --help              Show this help message
#
# Requirements:
#   - Docker with qemu-user-static (binfmt) configured: the ARMv7 models are
#     emulated on an amd64 host. The amd64 models are built inside the same
#     Debian 10 container because their glibc ceiling is the firmware's, not
#     the host's.
#   - Sibling checkouts: ../hsync-client and ../hsync-common.
#   - Network access on the first run: the builder images are built from
#     Docker Hub and mksapkg-OS5 is downloaded from WDCommunity/wdpksrc.
#
# Output:
#   wd-ex2-ultra-os5:
#     - dist/wd-ex2-ultra-os5/MyCloudEX2Ultra_hsync_<ver>.bin
#   wd-os5-all:
#     - dist/wd-os5/<MODEL>_hsync_<ver>.bin   one .bin per supported model
#
# Author: Alberto Basso
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Script directory (resolves symlinks)
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sibling checkouts. The packaged engine is always the client at these paths,
# so a .bin can never bundle a stale or foreign build.
readonly CLIENT_DIR="${SCRIPT_DIR}/../hsync-client"
readonly COMMON_DIR="${SCRIPT_DIR}/../hsync-common"

readonly APP_NAME="hsync"
# Entry point relative to the staged client tree.
readonly ENTRY_POINT="hsync_client/main.py"

readonly OUTPUT_BASE="dist"
readonly BUILD_DIR="build"

# -----------------------------------------------------------------------------
# Colors (disabled if not a terminal)
# -----------------------------------------------------------------------------

if [[ -t 1 ]]; then
    # ANSI-C quoting ($'...') so the variables hold the actual ESC byte and
    # render correctly with plain ``printf``/``cat`` as well as ``echo -e``.
    readonly RED=$'\033[0;31m'
    readonly GREEN=$'\033[0;32m'
    readonly YELLOW=$'\033[0;33m'
    readonly BLUE=$'\033[0;34m'
    readonly CYAN=$'\033[0;36m'
    readonly BOLD=$'\033[1m'
    readonly DIM=$'\033[2m'
    readonly RESET=$'\033[0m'
else
    readonly RED=''
    readonly GREEN=''
    readonly YELLOW=''
    readonly BLUE=''
    readonly CYAN=''
    readonly BOLD=''
    readonly DIM=''
    readonly RESET=''
fi

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------

log_info() { echo -e "${BLUE}ℹ${RESET} $*"; }
log_ok() { echo -e "${GREEN}✓${RESET} $*"; }
log_warn() { echo -e "${YELLOW}⚠${RESET} $*"; }
log_error() { echo -e "${RED}✕${RESET} $*" >&2; }
log_step() { echo -e "${CYAN}→${RESET} ${BOLD}$*${RESET}"; }

# -----------------------------------------------------------------------------
# WD OS5 configuration
# -----------------------------------------------------------------------------

readonly WDOS5_DIR="packaging"
readonly WDOS5_SRC_APKG="${WDOS5_DIR}/Apkg"
readonly WDOS5_OUTPUT_DIR="${OUTPUT_BASE}/wd-ex2-ultra-os5"
readonly WDOS5_BUILD_DIR="${BUILD_DIR}/wdos5"
readonly WDOS5_BUILDER_IMAGE="hsync-wdos5-builder:armv7"
readonly WDOS5_MKSAPKG_URL="https://raw.githubusercontent.com/WDCommunity/wdpksrc/master/mksapkg-OS5"
readonly WDOS5_CACHE_DIR="${WDOS5_DIR}/.cache"
readonly WDOS5_MKSAPKG="${WDOS5_CACHE_DIR}/mksapkg-OS5"
readonly WDOS5_MODEL="MyCloudEX2Ultra"
# Runtime image used to execute mksapkg-OS5 (see ``_build_mksapkg_image``).
readonly WDOS5_MKSAPKG_IMAGE="hsync-wdos5-mksapkg:bullseye"
readonly WDOS5_MKSAPKG_DOCKERFILE="${WDOS5_DIR}/Dockerfile.mksapkg"

# Minimal Docker build context staged by ``_stage_context``. It mirrors the
# ``hsync-client`` / ``hsync-common`` sibling layout so the builder image can
# install the path dependency and bake the sources (see
# packaging/Dockerfile.builder).
readonly WDOS5_CTX_DIR="${WDOS5_BUILD_DIR}/ctx"

# Models per CPU family. OS5 firmware ships glibc 2.30 at most, so every model
# is built against buster (glibc 2.28) regardless of the host.
readonly -a WDOS5_ARMV7_MODELS=("MyCloudEX2Ultra" "WDMyCloudMirror" "WDMyCloud" "WDCloud")
readonly -a WDOS5_AMD64_MODELS=(
    "WDMyCloudEX2100" "WDMyCloudEX4100" "WDMyCloudDL2100"
    "WDMyCloudDL4100" "MyCloudPR2100" "MyCloudPR4100"
)

# Version override, set by --version in main() and/or the HSYNC_VERSION
# environment variable. Mutable (not readonly) so main() can assign it.
VERSION_OVERRIDE=""

# PyInstaller flags shared by every WD OS5 build (single target and all-models).
# The entry point is intentionally last; ``_run_pyinstaller_in_docker`` appends
# the per-build --distpath/--workpath/--specpath after it.
# NOTE: backslash continuations (not embedded newlines) are used so the
# variable expands to a single line, keeping the ``pyinstaller`` command and
# its arguments on the same logical line.
readonly PYINSTALLER_COMMON_FLAGS="--clean --onedir --noconfirm --strip \
    --name ${APP_NAME} \
    --log-level ERROR \
    --hidden-import websockets.legacy \
    --hidden-import websockets.legacy.client \
    --hidden-import websockets.client \
    --hidden-import websockets.exceptions \
    --hidden-import watchdog.observers \
    --hidden-import watchdog.observers.inotify \
    --hidden-import watchdog.observers.inotify_buffer \
    --hidden-import watchdog.events \
    --hidden-import rich._unicode_data \
    --hidden-import rich._unicode_data._versions \
    --collect-submodules pathspec \
    --collect-submodules hsync_common \
    --exclude-module pytest --exclude-module pytest_asyncio \
    --exclude-module pytest_cov --exclude-module tkinter \
    --exclude-module unittest --exclude-module pdb \
    --exclude-module doctest --exclude-module pip \
    --exclude-module setuptools --exclude-module wheel \
    --exclude-module pkg_resources --exclude-module rapidfuzz \
    ${ENTRY_POINT}"

# -----------------------------------------------------------------------------
# Version helpers
# -----------------------------------------------------------------------------

# Version declared by the sibling client's pyproject.toml.
_client_version() {
    grep -E '^version[[:space:]]*=' "${CLIENT_DIR}/pyproject.toml" | head -1 |
        sed 's/.*"\(.*\)".*/\1/'
}

# Version the frozen engine reports: the single source of truth shared by every
# HSYNC component (hsync_common.constants.HSYSYNC_VERSION).
_engine_version() {
    grep -E '^HSYNC_VERSION[[:space:]]*=' "${COMMON_DIR}/hsync_common/constants.py" | head -1 |
        sed 's/.*"\(.*\)".*/\1/'
}

# Get the packaged (SemVer) version: --version flag > HSYNC_VERSION env >
# the sibling client's pyproject.toml.
get_version() {
    if [[ -n "${VERSION_OVERRIDE}" ]]; then
        printf '%s' "${VERSION_OVERRIDE}"
    elif [[ -n "${HSYNC_VERSION:-}" ]]; then
        printf '%s' "${HSYNC_VERSION}"
    else
        _client_version
    fi
}

# Refuse to package an engine whose version does not match the version stamped
# into apkg.rc/VERSION/the .bin name. A suffix (prerelease or build metadata) is
# allowed on top of the engine version, never a different base version.
_verify_embedded_version() {
    local version="$1" client engine
    client="$(_client_version)"
    engine="$(_engine_version)"

    if [[ -z "${client}" || -z "${engine}" ]]; then
        log_error "Cannot read the client version (${CLIENT_DIR}/pyproject.toml)"
        log_error "or HSYNC_VERSION (${COMMON_DIR}/hsync_common/constants.py)."
        exit 1
    fi
    if [[ "${client}" != "${engine}" ]]; then
        log_error "Sibling checkouts disagree: hsync-client ${client} but hsync-common ${engine}."
        log_error "Update both checkouts before packaging."
        exit 1
    fi

    case "${version}" in
        "${engine}"|"${engine}"-*|"${engine}"+*) ;;
        *)
            log_error "Version ${version} does not match the bundled engine ${engine}."
            log_error "Only a suffix may be added (e.g. ${engine}-alpha.1)."
            exit 1
            ;;
    esac
    log_ok "Packaging hsync ${version} (engine ${engine})"
}

# -----------------------------------------------------------------------------
# Environment helpers
# -----------------------------------------------------------------------------

# Report whether a binfmt_misc handler exists and is enabled.
# $1 = handler name (e.g. qemu-arm, qemu-aarch64)
qemu_handler_active() {
    local path="/proc/sys/fs/binfmt_misc/$1"
    [[ -e "${path}" ]] && grep -q '^enabled' "${path}" 2>/dev/null
}

# Ensure the qemu-user-static binfmt handlers required for cross-arch Docker
# emulation are registered AND activate. When a handler is missing the emulated
# layers die deep inside the build with a cryptic "exec format error", so the
# registration is idempotent and fails loudly when it cannot be activated.
# $@ = required handler names (default: qemu-arm)
ensure_qemu_binfmt() {
    local handlers=("$@")
    [[ ${#handlers[@]} -eq 0 ]] && handlers=("qemu-arm")

    log_step "Ensuring qemu-user-static binfmt handlers are active: ${handlers[*]}"

    local h missing=()
    for h in "${handlers[@]}"; do
        qemu_handler_active "${h}" || missing+=("${h}")
    done
    if [[ ${#missing[@]} -eq 0 ]]; then
        log_ok "binfmt handlers already active"
        return 0
    fi

    log_info "Registering qemu-user-static binfmt handlers..."
    # Image pinned by digest: this runs --privileged, so it must not move.
    if ! docker run --rm --privileged \
        multiarch/qemu-user-static@sha256:fe60359c92e86a43cc87b3d906006245f77bfc0565676b80004cc666e4feb9f0 \
        --reset -p yes \
        >/dev/null 2>&1; then
        log_error "Failed to run multiarch/qemu-user-static (is the Docker daemon reachable?)."
        exit 1
    fi

    missing=()
    for h in "${handlers[@]}"; do
        qemu_handler_active "${h}" || missing+=("${h}")
    done
    if [[ ${#missing[@]} -ne 0 ]]; then
        log_error "binfmt handlers still inactive after registration: ${missing[*]}"
        log_error "Cross-arch emulation is unavailable; aborting now to avoid a"
        log_error "misleading 'exec format error' later in the build."
        exit 1
    fi
    log_ok "binfmt handlers registered and active"
}

# Emit the path of the cached mksapkg-OS5, downloading it on first use.
_mksapkg_tool() {
    if [[ ! -x "${WDOS5_MKSAPKG}" ]]; then
        mkdir -p "${WDOS5_CACHE_DIR}"
        log_step "Fetching mksapkg-OS5 from WDCommunity/wdpksrc..."
        curl -fsSL "${WDOS5_MKSAPKG_URL}" -o "${WDOS5_MKSAPKG}"
        chmod 0755 "${WDOS5_MKSAPKG}"
    fi
    printf '%s' "${WDOS5_MKSAPKG}"
}

# Fail early (with an actionable message) when the sibling sources are missing.
check_prerequisites() {
    local missing=0
    if [[ ! -f "${CLIENT_DIR}/pyproject.toml" ]]; then
        log_error "hsync-client checkout not found at ${CLIENT_DIR}"
        missing=1
    fi
    if [[ ! -f "${COMMON_DIR}/pyproject.toml" ]]; then
        log_error "hsync-common checkout not found at ${COMMON_DIR}"
        missing=1
    fi
    if [[ ! -d "${WDOS5_SRC_APKG}" ]]; then
        log_error "Packaging tree missing: ${WDOS5_SRC_APKG}"
        missing=1
    fi
    if [[ ${missing} -ne 0 ]]; then
        log_info "Clone hsync-client and hsync-common as siblings of this repository."
        exit 1
    fi

    if ! command -v docker >/dev/null 2>&1; then
        log_error "docker is required for every WD OS5 target."
        exit 1
    fi
}

# Display usage information
show_help() {
    cat << EOF
${BOLD}HSYNC WD OS5 - Build Script${RESET}

${BOLD}Usage:${RESET}
    ./compile.sh [options]

${BOLD}Options:${RESET}
    -c, --clean             Clean build artifacts before building
    -t, --target TARGET     Build target (default: wd-os5-all)
                            Supported: wd-os5-all, wd-ex2-ultra-os5
    -v, --version VERSION   Override the packaged version (default: the
                            hsync-client version). Also settable via
                            HSYNC_VERSION.
    -h, --help              Show this help message

${BOLD}Examples:${RESET}
    ./compile.sh                              # All 10 models (ARMv7 + amd64)
    ./compile.sh --clean                      # Clean and rebuild
    ./compile.sh --target wd-ex2-ultra-os5    # EX2 Ultra only (ARMv7)
    ./compile.sh -t wd-os5-all -v 1.2.0       # Pin the packaged version

${BOLD}Output:${RESET}
    wd-ex2-ultra-os5:
        ${WDOS5_OUTPUT_DIR}/${WDOS5_MODEL}_${APP_NAME}_<ver>.bin
    wd-os5-all:
        ${OUTPUT_BASE}/wd-os5/<MODEL>_${APP_NAME}_<ver>.bin (one per model)
EOF
}

# Remove build artifacts (dist/, build/) from a previous run.
clean_artifacts() {
    log_step "Cleaning build artifacts..."

    local cleaned=0
    if [[ -d "${OUTPUT_BASE}" ]]; then
        rm -rf "${OUTPUT_BASE}"
        ((cleaned++)) || true
    fi
    if [[ -d "${BUILD_DIR}" ]]; then
        rm -rf "${BUILD_DIR}"
        ((cleaned++)) || true
    fi
    if [[ ${cleaned} -gt 0 ]]; then
        log_ok "Cleaned ${cleaned} artifact(s)"
    else
        log_info "No artifacts to clean"
    fi
}

# Remove the locally built builder/mksapkg images so the next run rebuilds them.
clean_images() {
    log_step "Removing builder images..."
    docker image rm -f \
        "${WDOS5_BUILDER_IMAGE}" \
        "hsync-wdos5-builder:amd64" \
        "${WDOS5_MKSAPKG_IMAGE}" >/dev/null 2>&1 || true
    log_ok "Builder images removed"
}

# -----------------------------------------------------------------------------
# Docker helpers
# -----------------------------------------------------------------------------

# Build the small amd64 image that runs mksapkg-OS5. The upstream tool is a
# prebuilt x86-64 binary linked against ``libxml2.so.2`` and it shells out to
# ``openssl bf-cbc`` (a legacy cipher) to sign apkg.sign. Modern hosts no longer
# provide either — e.g. Ubuntu 26.04 ships libxml2 ``.so.16`` only, and OpenSSL 3
# hides bf-cbc behind the legacy provider — so the tool runs inside a Debian
# bullseye container that still carries libxml2.so.2 and an OpenSSL 1.1.1 with
# bf-cbc enabled by default (see Dockerfile.mksapkg). Cached after first build.
_build_mksapkg_image() {
    log_step "Building mksapkg runtime image ${WDOS5_MKSAPKG_IMAGE} (cached after first run)..."
    DOCKER_BUILDKIT=1 docker build \
        --platform linux/amd64 \
        -t "${WDOS5_MKSAPKG_IMAGE}" \
        -f "${WDOS5_MKSAPKG_DOCKERFILE}" \
        "${WDOS5_DIR}"
}

# Run mksapkg-OS5 against a staged package tree inside the runtime image.
# mksapkg-OS5 has no output-path flag: it ``cd ..`` and drops the .bin in the
# parent of its working directory, so the staging dir's parent is mounted at
# /work and the staging dir itself is the container CWD. Running with the host
# uid keeps the produced artifacts owned by the caller.
# Args: stage_abs  model  mksapkg_abs
_run_mksapkg() {
    local stage_abs="$1" model="$2" mksapkg_rel="$3"
    local stage_parent stage_name mksapkg_abs
    stage_parent="$(dirname "${stage_abs}")"
    stage_name="$(basename "${stage_abs}")"
    mksapkg_abs="$(cd "$(dirname "${mksapkg_rel}")" && pwd)/$(basename "${mksapkg_rel}")"
    docker run --rm \
        --platform linux/amd64 \
        -u "$(id -u):$(id -g)" \
        -v "${stage_parent}:/work" \
        -v "${mksapkg_abs}:/usr/local/bin/mksapkg-OS5:ro" \
        -w "/work/${stage_name}" \
        "${WDOS5_MKSAPKG_IMAGE}" \
        mksapkg-OS5 -E -s -m "${model}"
}

# Stage the minimal Docker build context consumed by Dockerfile.builder.
#
# The builder image installs the client's dependencies and bakes the sources as
# cached layers, so the context must expose both sibling projects in their
# relative ``../hsync-common`` layout. __pycache__ directories are pruned to
# keep the context (and therefore the layer cache) stable across runs.
_stage_context() {
    log_step "Staging Docker build context at ${WDOS5_CTX_DIR}..."
    rm -rf "${WDOS5_CTX_DIR}"
    mkdir -p "${WDOS5_CTX_DIR}/hsync-client" "${WDOS5_CTX_DIR}/hsync-common"
    cp -a "${CLIENT_DIR}/pyproject.toml" "${CLIENT_DIR}/poetry.lock" \
        "${CLIENT_DIR}/README.md" "${WDOS5_CTX_DIR}/hsync-client/"
    cp -a "${CLIENT_DIR}/hsync_client" "${WDOS5_CTX_DIR}/hsync-client/"
    cp -a "${COMMON_DIR}/pyproject.toml" "${COMMON_DIR}/README.md" \
        "${WDOS5_CTX_DIR}/hsync-common/"
    cp -a "${COMMON_DIR}/hsync_common" "${WDOS5_CTX_DIR}/hsync-common/"
    find "${WDOS5_CTX_DIR}" -name __pycache__ -type d -prune -exec rm -rf {} +
}

# Build the builder image for one CPU family.
# Args: docker_platform  base_image  builder_tag
_docker_build() {
    local docker_platform="$1" base_image="$2" builder_tag="$3"
    log_step "Building Docker image ${builder_tag} (cached after first run)..."
    DOCKER_BUILDKIT=1 docker build \
        --platform "${docker_platform}" \
        --build-arg "BASE_IMAGE=${base_image}" \
        --build-arg "TARGET_PLATFORM=${docker_platform}" \
        -t "${builder_tag}" \
        -f "${WDOS5_DIR}/Dockerfile.builder" \
        "${WDOS5_CTX_DIR}"
}

# Run PyInstaller inside the pre-built builder image. Dependencies and sources
# are already baked into the image, so this step only produces the frozen
# binary. The host ${out_dir} is mounted at /out; PyInstaller writes /out/bin
# (the onedir bundle) and /out/work (intermediates).
# Args: docker_platform  out_dir  builder_tag
_run_pyinstaller_in_docker() {
    local docker_platform="$1" out_dir="$2" builder_tag="$3"
    local out_abs
    mkdir -p "${out_dir}"
    out_abs="$(cd "${out_dir}" && pwd)"
    # Run as the host uid:gid so the produced bundle under /out (the host
    # ${out_dir}, e.g. build/wdos5) is owned by the caller and not root —
    # otherwise the host-side cleanup (rm -rf build) of a later --clean run
    # fails with "Permission denied". HOME/XDG_CACHE_HOME are pointed at /tmp
    # because an arbitrary uid has no writable home for PyInstaller's cache.
    docker run --rm \
        --platform "${docker_platform}" \
        -u "$(id -u):$(id -g)" \
        -e HOME=/tmp -e XDG_CACHE_HOME=/tmp \
        -v "${out_abs}:/out" \
        -w /build/hsync-client \
        -e LC_ALL=C -e PYTHONWARNINGS=ignore \
        "${builder_tag}" \
        pyinstaller \
            ${PYINSTALLER_COMMON_FLAGS} \
            --distpath /out/bin \
            --workpath /out/work \
            --specpath /out/work
}

# -----------------------------------------------------------------------------
# Package staging
# -----------------------------------------------------------------------------

# Materialise a disposable package tree: the committed Apkg/ copy, the icon at
# the path apkg.rc declares, the rendered version and its VERSION stamp.
# mksapkg-OS5 packs the tree in place, so the source tree is never mutated.
# Args: stage_dir  version
_stage_package_tree() {
    local stage_dir="$1" version="$2"
    rm -rf "${stage_dir}"
    mkdir -p "${stage_dir}"
    cp -a "${WDOS5_SRC_APKG}/." "${stage_dir}/"

    # apkg.rc declares ``Icon: hsync.png`` at the package root while the web UI
    # serves the same file from web/; keep the committed web/hsync.png as the
    # single source and place it where the package manager looks for it.
    cp -f "${WDOS5_SRC_APKG}/web/hsync.png" "${stage_dir}/hsync.png"

    # Lifecycle hook scripts must be executable or the install on the NAS fails
    # silently.
    chmod 0755 "${stage_dir}"/*.sh 2>/dev/null || true

    sed -i.bak -e "s/__HSYNC_VERSION__/${version}/g" "${stage_dir}/apkg.rc"
    rm -f "${stage_dir}/apkg.rc.bak"
    echo "${version}" > "${stage_dir}/VERSION"
}

# Copy the frozen bundle into the staged package (--onedir layout:
# bin/<APP_NAME>/<APP_NAME>) and mark the entry point executable.
# Args: stage_dir  binary_dir
_install_binary() {
    local stage_dir="$1" binary_dir="$2"
    if [[ ! -f "${binary_dir}/${APP_NAME}" ]]; then
        log_error "Frozen engine missing at ${binary_dir}/${APP_NAME}"
        exit 1
    fi
    mkdir -p "${stage_dir}/bin"
    cp -a "${binary_dir}" "${stage_dir}/bin/"
    chmod 0755 "${stage_dir}/bin/${APP_NAME}/${APP_NAME}"
}

# Package one model from an already-built binary of its CPU family.
# Args: model  binary_dir  version  stage_base  out_abs  mksapkg
_wdos5_package_model() {
    local model="$1" binary_dir="$2" version="$3"
    local stage_base="$4" out_abs="$5" mksapkg="$6"

    # The inner directory **must** be named after the package (APP_NAME):
    # mksapkg-OS5 tars its CWD basename verbatim and OS5 rejects packages whose
    # tar root is not the Package: name with ``Failed to load the app package``.
    local stage_dir="${stage_base}/${model}/${APP_NAME}"
    _stage_package_tree "${stage_dir}" "${version}"
    _install_binary "${stage_dir}" "${binary_dir}"

    local stage_abs stage_parent
    stage_abs="$(cd "${stage_dir}" && pwd)"
    stage_parent="$(dirname "${stage_abs}")"

    # mksapkg-OS5 drops the .bin in the *parent* of its CWD; clear stale
    # artifacts there so the lookup below picks up the fresh one.
    rm -f "${stage_parent}/${model}_${APP_NAME}_"*.bin*
    _run_mksapkg "${stage_abs}" "${model}" "${mksapkg}"

    # `|| true`: with `set -e` + `pipefail` an unmatched glob would abort the
    # script before the explicit diagnostic below could run.
    local produced bin_name
    produced="$(ls -t "${stage_parent}/${model}_${APP_NAME}_"*.bin* 2>/dev/null | head -1 || true)"
    if [[ -z "${produced}" || ! -f "${produced}" ]]; then
        log_error "mksapkg-OS5 did not produce a .bin for ${model}"
        exit 1
    fi
    # Normalise the mksapkg-OS5 name (it appends the build date, MMDDYYYY,
    # after the .bin extension) to a clean, deterministic one; the dashboard
    # validates the signed payload (apkg.sign), not the file name.
    bin_name="${model}_${APP_NAME}_${version}.bin"
    mv -f "${produced}" "${out_abs}/${bin_name}"
    log_ok "  → ${bin_name}"
}

# -----------------------------------------------------------------------------
# Build targets
# -----------------------------------------------------------------------------

# Build the .bin installer for My Cloud EX2 Ultra (ARMv7).
build_wd_os5() {
    local version
    version="$(get_version)"

    log_step "Building ${APP_NAME} v${version} for wd-ex2-ultra-os5 (ARMv7)..."
    check_prerequisites
    _verify_embedded_version "${version}"

    mkdir -p "${WDOS5_OUTPUT_DIR}" "${WDOS5_CACHE_DIR}" "${WDOS5_BUILD_DIR}"
    local out_abs
    out_abs="$(cd "${WDOS5_OUTPUT_DIR}" && pwd)"

    ensure_qemu_binfmt qemu-arm
    _stage_context
    _docker_build linux/arm/v7 arm32v7/debian:buster "${WDOS5_BUILDER_IMAGE}"

    # The image already carries the installed deps and sources, so this only
    # produces the frozen binary under build/wdos5/bin/, keeping the source
    # tree clean for the staging step below.
    log_step "Running PyInstaller inside the ARMv7 container..."
    _run_pyinstaller_in_docker linux/arm/v7 "${WDOS5_BUILD_DIR}" "${WDOS5_BUILDER_IMAGE}"

    local built_dir="${WDOS5_BUILD_DIR}/bin/${APP_NAME}"
    if [[ ! -d "${built_dir}" ]]; then
        log_error "ARMv7 build directory not produced at ${built_dir}"
        exit 1
    fi

    local mksapkg
    mksapkg="$(_mksapkg_tool)"
    _build_mksapkg_image

    log_step "Building OS5 .bin package..."
    _wdos5_package_model "${WDOS5_MODEL}" "${built_dir}" "${version}" \
        "${WDOS5_BUILD_DIR}/stage" "${out_abs}" "${mksapkg}"

    local bin_path="${out_abs}/${WDOS5_MODEL}_${APP_NAME}_${version}.bin"
    if [[ ! -f "${bin_path}" ]]; then
        log_error "WD OS5 package not produced at ${bin_path}"
        exit 1
    fi
    local size
    size="$(du -h "${bin_path}" | cut -f1)"

    echo
    log_ok "WD OS5 package built!"
    echo
    echo -e "  ${BOLD}Model:${RESET}    ${WDOS5_MODEL}"
    echo -e "  ${BOLD}Arch:${RESET}     linux/arm/v7 (glibc <= 2.28 / works up to 2.30)"
    echo -e "  ${BOLD}Size:${RESET}     ${size}"
    echo -e "  ${BOLD}Version:${RESET}  ${version}"
    echo
    echo -e "${DIM}Install via My Cloud OS5 dashboard:${RESET}"
    echo -e "${DIM}  Apps → Install an App manually → choose this .bin${RESET}"
    echo
    local sep="────────────────────────────────────────────────────────────"
    echo -e "${GREEN}${BOLD}${sep}${RESET}"
    echo -e "${GREEN}${BOLD}  📦  Installation package:${RESET}"
    echo -e "${GREEN}${BOLD}      ${bin_path}${RESET}"
    echo -e "${GREEN}${BOLD}${sep}${RESET}"
}

# Build .bin installers for every supported WD My Cloud OS5 model (10 total).
#
# Two Docker builds are performed — one per CPU family — and the same
# PyInstaller binary is shared across all models of that family:
#
#   ARMv7 (4 models) → arm32v7/debian:buster
#   amd64 (6 models) → amd64/debian:buster
#
# Output: dist/wd-os5/<MODEL>_hsync_<ver>.bin
build_wd_os5_all() {
    local version
    version="$(get_version)"

    log_step "Building ${APP_NAME} v${version} for all 10 WD My Cloud OS5 models..."
    check_prerequisites
    _verify_embedded_version "${version}"

    local all_out="${OUTPUT_BASE}/wd-os5"
    local all_build="${WDOS5_BUILD_DIR}/all"
    mkdir -p "${all_out}" "${WDOS5_CACHE_DIR}" "${all_build}"

    local mksapkg
    mksapkg="$(_mksapkg_tool)"
    _build_mksapkg_image

    ensure_qemu_binfmt qemu-arm
    _stage_context

    # ── ARMv7 binary ────────────────────────────────────────────────────────
    echo
    log_step "─── ARMv7 build ───────────────────────────────────────"
    local armv7_tag="hsync-wdos5-builder:armv7"
    local armv7_out="${all_build}/armv7"
    local armv7_binary="${armv7_out}/bin/${APP_NAME}"

    _docker_build linux/arm/v7 arm32v7/debian:buster "${armv7_tag}"
    log_step "Compiling ARMv7 binary inside container..."
    _run_pyinstaller_in_docker linux/arm/v7 "${armv7_out}" "${armv7_tag}"

    if [[ ! -d "${armv7_binary}" ]]; then
        log_error "ARMv7 build directory not produced at ${armv7_binary}"
        exit 1
    fi
    log_ok "ARMv7 binary ready ($(du -sh "${armv7_binary}" | cut -f1))"

    # ── amd64 binary ────────────────────────────────────────────────────────
    echo
    log_step "─── amd64 build ───────────────────────────────────────"
    local amd64_tag="hsync-wdos5-builder:amd64"
    local amd64_out="${all_build}/amd64"
    local amd64_binary="${amd64_out}/bin/${APP_NAME}"

    _docker_build linux/amd64 amd64/debian:buster "${amd64_tag}"
    log_step "Compiling amd64 binary inside container..."
    _run_pyinstaller_in_docker linux/amd64 "${amd64_out}" "${amd64_tag}"

    if [[ ! -d "${amd64_binary}" ]]; then
        log_error "amd64 build directory not produced at ${amd64_binary}"
        exit 1
    fi
    log_ok "amd64 binary ready ($(du -sh "${amd64_binary}" | cut -f1))"

    # ── Package every model ─────────────────────────────────────────────────
    local stage_base="${all_build}/stage"
    local out_abs
    out_abs="$(cd "${all_out}" && pwd)"

    echo
    log_step "─── Packaging ARMv7 models (${#WDOS5_ARMV7_MODELS[@]}) ───────────────────"
    local model
    for model in "${WDOS5_ARMV7_MODELS[@]}"; do
        _wdos5_package_model "${model}" "${armv7_binary}" "${version}" \
            "${stage_base}" "${out_abs}" "${mksapkg}"
    done

    echo
    log_step "─── Packaging amd64 models (${#WDOS5_AMD64_MODELS[@]}) ───────────────────"
    for model in "${WDOS5_AMD64_MODELS[@]}"; do
        _wdos5_package_model "${model}" "${amd64_binary}" "${version}" \
            "${stage_base}" "${out_abs}" "${mksapkg}"
    done

    # ── Summary ─────────────────────────────────────────────────────────────
    local total=$(( ${#WDOS5_ARMV7_MODELS[@]} + ${#WDOS5_AMD64_MODELS[@]} ))
    echo
    log_ok "All ${total} WD OS5 packages built!"
    echo
    echo -e "  ${BOLD}Version:${RESET}   ${version}"
    echo -e "  ${BOLD}Output:${RESET}    ${out_abs}/"
    echo
    echo -e "  ${BOLD}ARMv7 (${#WDOS5_ARMV7_MODELS[@]}):${RESET}  ${WDOS5_ARMV7_MODELS[*]}"
    echo -e "  ${BOLD}amd64 (${#WDOS5_AMD64_MODELS[@]}):${RESET}  ${WDOS5_AMD64_MODELS[*]}"
    echo
    local sep="────────────────────────────────────────────────────────────"
    echo -e "${GREEN}${BOLD}${sep}${RESET}"
    echo -e "${GREEN}${BOLD}  📦  Installation packages:${RESET}"
    local f
    for f in "${out_abs}/"*_"${APP_NAME}"_*.bin; do
        [[ -f "${f}" ]] && echo -e "${GREEN}${BOLD}      $(basename "${f}")${RESET}"
    done
    echo -e "${GREEN}${BOLD}${sep}${RESET}"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    local do_clean=false
    local target="wd-os5-all"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--clean)
                do_clean=true
                shift
                ;;
            -t|--target)
                [[ $# -ge 2 ]] || { log_error "--target requires a value"; exit 1; }
                target="$2"
                shift 2
                ;;
            -v|--version)
                [[ $# -ge 2 ]] || { log_error "--version requires a value"; exit 1; }
                VERSION_OVERRIDE="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done

    cd "${SCRIPT_DIR}"

    echo -e "${BOLD}HSYNC WD OS5 - Build${RESET}"
    echo -e "${DIM}─────────────────────${RESET}"
    echo

    case "${target}" in
        wd-ex2-ultra-os5)
            if [[ "${do_clean}" == true ]]; then
                clean_artifacts
                clean_images
                echo
            fi
            build_wd_os5
            ;;
        wd-os5-all)
            if [[ "${do_clean}" == true ]]; then
                clean_artifacts
                clean_images
                echo
            fi
            build_wd_os5_all
            ;;
        *)
            log_error "Unknown target: ${target}"
            echo "Supported targets: wd-os5-all, wd-ex2-ultra-os5"
            exit 1
            ;;
    esac
}

# Run only when executed, so tests can source the helpers without building.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi


