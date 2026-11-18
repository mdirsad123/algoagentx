#!/usr/bin/env bash
# One-time privileged setup for Oracle Ubuntu RustDesk manager.
# It grants passwordless sudo ONLY for three fixed actions in a root-owned script.
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo '[ERROR] This installer must be run once with sudo.' >&2
  exit 1
fi
if ! id ubuntu >/dev/null 2>&1; then
  echo '[ERROR] The expected Linux user "ubuntu" does not exist.' >&2
  exit 1
fi
if ! command -v rustdesk >/dev/null 2>&1; then
  echo '[ERROR] RustDesk is not installed on this Ubuntu host.' >&2
  exit 1
fi
if [[ ! -x /usr/sbin/visudo ]]; then
  echo '[ERROR] visudo is missing. Cannot safely install sudoers permission.' >&2
  exit 1
fi

install -d -o root -g root -m 0755 /usr/local/sbin
cat > /usr/local/sbin/rustdesk-server-manager <<'MANAGER'
#!/usr/bin/env bash
# Restricted root-owned management wrapper. This file must not be user-writable.
set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
  echo 'Usage: rustdesk-server-manager {add|remove|check}' >&2
  exit 2
fi

case "$1" in
  add)
    systemctl is-active --quiet rustdesk || { echo '[ERROR] RustDesk service is not active.' >&2; exit 1; }
    rustdesk --option custom-rendezvous-server '3.7.212.218'
    rustdesk --option relay-server '3.7.212.218'
    rustdesk --option api-server ''
    rustdesk --option key 'AUHZTMDlcAxbTTDSL71U4hp4KZPDEbMQCggFTmkbFuc='
    systemctl restart rustdesk
    systemctl is-active --quiet rustdesk
    echo '[OK] ADD_COMPLETED: Custom ID/Relay/Key configured; API blank; RustDesk restarted.'
    ;;
  remove)
    systemctl is-active --quiet rustdesk || { echo '[ERROR] RustDesk service is not active.' >&2; exit 1; }
    rustdesk --option custom-rendezvous-server ''
    rustdesk --option relay-server ''
    rustdesk --option api-server ''
    rustdesk --option key ''
    systemctl restart rustdesk
    systemctl is-active --quiet rustdesk
    echo '[OK] REMOVE_COMPLETED: All four settings cleared; RustDesk restarted.'
    ;;
  check)
    echo '=== RustDesk service ==='
    systemctl is-active rustdesk || true
    echo '=== RustDesk version ==='
    rustdesk --version || true
    echo '=== ID Server ==='
    rustdesk --option custom-rendezvous-server
    echo '=== Relay Server ==='
    rustdesk --option relay-server
    echo '=== API Server ==='
    rustdesk --option api-server
    echo '=== Public Key ==='
    rustdesk --option key
    echo '=== Ubuntu RustDesk ID ==='
    rustdesk --get-id
    ;;
  *)
    echo '[ERROR] Only add, remove and check are allowed.' >&2
    exit 2
    ;;
esac
MANAGER
chown root:root /usr/local/sbin/rustdesk-server-manager
chmod 0755 /usr/local/sbin/rustdesk-server-manager

SUDOERS=/etc/sudoers.d/90-rustdesk-server-manager
cat > "$SUDOERS" <<'SUDOERS_FILE'
# Passwordless permission only for the root-owned restricted RustDesk wrapper.
# Do NOT grant NOPASSWD: ALL or NOPASSWD: /usr/bin/rustdesk *.
ubuntu ALL=(root) NOPASSWD: /usr/local/sbin/rustdesk-server-manager add, /usr/local/sbin/rustdesk-server-manager remove, /usr/local/sbin/rustdesk-server-manager check
SUDOERS_FILE
chown root:root "$SUDOERS"
chmod 0440 "$SUDOERS"
if ! /usr/sbin/visudo -cf "$SUDOERS"; then
  rm -f "$SUDOERS"
  echo '[ERROR] Sudo configuration was invalid and has been removed.' >&2
  exit 1
fi

echo
printf '%s\n' '[OK] Passwordless access configured for three restricted RustDesk actions.' \
 '     ADD / REMOVE / CHECK will not request an Ubuntu sudo password.' \
 '     SSH authentication still uses your private key.' \
 '     No other sudo privileges have been changed.'
