#!/usr/bin/env bash
#
# sign_ssh_key.sh – sign an SSH public key (or a freshly‑generated Ed25519 key)
# using only the permit‑pty and permit‑port‑forwarding extensions.
#
# ASSUMPTION:
#   The `private_key_file` value in ansible.cfg is an **absolute** path.
#   It may still contain ${HOME}, $HOME or a leading ~, which are expanded.
#
# FEATURES (unchanged from the previous version):
#   • Default validity = +30m if -v is omitted.
#   • By default a new Ed25519 key pair is generated.
#   • Use -e <pubkey> to sign an existing key pair; the script copies the
#     existing private key into the location defined by ansible.cfg.
#   • Certificate is written as <basename>-cert.pub in the same directory.
#
# -------------------------------------------------------------------------
# CONFIGURATION ------------------------------------------------------------
# Change this only if you move ansible.cfg to another location.
# ANSIBLE_CFG_PATH="/new/path/to/ansible.cfg"
ANSIBLE_CFG_PATH="$(dirname "$(realpath "${BASH_SOURCE[0]}")")/ansible.cfg"
# -------------------------------------------------------------------------

set -euo pipefail

# ---------- Helper functions ----------
usage() {
    grep '^#' "$0" | sed -e 's/^# //;s/^#//'
    exit 1
}
error_exit() {
    echo "Error: $*" >&2
    exit 1
}

# Expand a path that may contain ~, $VAR or ${VAR}
expand_path() {
    local raw expanded
    raw="$1"

    # Replace a leading ~ with $HOME
    if [[ "$raw" == "~"* ]]; then
        raw="${HOME}${raw:1}"
    fi

    # Let the shell expand $VAR / ${VAR}
    eval "expanded=\"$raw\""
    printf '%s' "$expanded"
}

# ---------- Extract private_key_file from ansible.cfg ----------
extract_private_key_path() {
    local cfg_file key_line raw_path expanded_path

    cfg_file="${ANSIBLE_CFG_PATH}"
    [[ -f "$cfg_file" ]] || error_exit "ansible.cfg not found at '${cfg_file}'."

    # Grab the line that defines private_key_file (ignore comments/spaces)
    key_line=$(grep -E '^\s*private_key_file\s*=' "$cfg_file" || true)
    [[ -n "$key_line" ]] || error_exit "'private_key_file' not defined in '${cfg_file}'."

    # Value after '=', strip surrounding spaces and quotes
    raw_path=$(echo "$key_line" | cut -d'=' -f2- | tr -d ' "' )

    # At this point we expect an absolute path; we just expand env vars / ~
    expanded_path=$(expand_path "$raw_path")
    printf '%s' "$expanded_path"
}

# ---------- Parse command‑line arguments ----------
CA_KEY=""
IDENTITY=""
PRINCIPALS=""
VALIDITY="+30m"          # default when -v is omitted
USE_EXISTING=false

while getopts ":c:i:p:v:e:h" opt; do
    case "${opt}" in
        c) CA_KEY="${OPTARG}" ;;
        i) IDENTITY="${OPTARG}" ;;
        p) PRINCIPALS="${OPTARG}" ;;
        v) VALIDITY="${OPTARG}" ;;
        e) USE_EXISTING=true ; EXISTING_PUBKEY="${OPTARG}" ;;
        h) usage ;;
        *) error_exit "Invalid option: -${OPTARG}" ;;
    esac
done
shift $((OPTIND-1))

# ---------- Validate required inputs ----------
[[ -z "${CA_KEY}" ]] && error_exit "CA key (-c) is required."
[[ -z "${IDENTITY}" ]] && error_exit "Identity (-i) is required."
[[ -z "${PRINCIPALS}" ]] && error_exit "Principals (-p) are required."
# VALIDITY already has a default, so no extra check needed.

# ---------- Resolve the absolute private‑key location ----------
PRIVATE_KEY_PATH=$(extract_private_key_path)
PRIVATE_KEY_DIR=$(dirname "$PRIVATE_KEY_PATH")
PRIVATE_KEY_BASENAME=$(basename "$PRIVATE_KEY_PATH")

# Ensure the target directory exists
mkdir -p "$PRIVATE_KEY_DIR"

# ---------- Main workflow ----------
if ${USE_EXISTING}; then
    # ----- USER supplied an existing key pair -----
    PUBKEY_FILE="${EXISTING_PUBKEY}"
    [[ -f "${PUBKEY_FILE}" ]] || error_exit "Provided public key '${PUBKEY_FILE}' does not exist."

    # Corresponding private key (same name without .pub)
    PRIVATE_SRC="${PUBKEY_FILE%.pub}"
    [[ -f "${PRIVATE_SRC}" ]] || error_exit "Corresponding private key '${PRIVATE_SRC}' not found."

    # Copy both private and public keys into the location from ansible.cfg
    PRIVATE_KEY_FULL="${PRIVATE_KEY_PATH}"
    PUBLIC_KEY_FULL="${PRIVATE_KEY_FULL}.pub"

    echo "Copying existing private key to '${PRIVATE_KEY_FULL}' ..."
    cp -p "${PRIVATE_SRC}" "${PRIVATE_KEY_FULL}"
    chmod 600 "${PRIVATE_KEY_FULL}"

    echo "Copying existing public key to '${PUBLIC_KEY_FULL}' ..."
    cp -p "${PUBKEY_FILE}" "${PUBLIC_KEY_FULL}"

    SIGN_PUBKEY="${PUBLIC_KEY_FULL}"
else
    # ----- DEFAULT: generate a fresh Ed25519 key pair -----
    PRIVATE_KEY_FULL="${PRIVATE_KEY_PATH}"
    PUBLIC_KEY_FULL="${PRIVATE_KEY_FULL}.pub"

    echo "Generating fresh Ed25519 key pair at '${PRIVATE_KEY_FULL}' ..."
    ssh-keygen -t ed25519 -f "${PRIVATE_KEY_FULL}" -N "" -q -C "${IDENTITY}"

    SIGN_PUBKEY="${PUBLIC_KEY_FULL}"
fi

# ----- Determine certificate filename (standard OpenSSH naming) -----
CERT_FILE="${PRIVATE_KEY_DIR}/${PRIVATE_KEY_BASENAME}-cert.pub"

# ----- Sign the key -----
echo "Signing '${SIGN_PUBKEY}' with CA key '${CA_KEY}' ..."
ssh-keygen -s "${CA_KEY}" \
          -I "${IDENTITY}" \
          -n "${PRINCIPALS}" \
          -V "${VALIDITY}" \
          -z "$(date +%s)" \
          -O extension:permit-pty \
          -O extension:permit-port-forwarding \
          -f "${CERT_FILE}" \
          "${SIGN_PUBKEY}"

echo "✅ Certificate written to ${CERT_FILE}"
if ${USE_EXISTING}; then
    echo "🔑 Existing private key was copied to ${PRIVATE_KEY_FULL}"
else
    echo "🔑 Newly generated private key located at ${PRIVATE_KEY_FULL}"
fi
