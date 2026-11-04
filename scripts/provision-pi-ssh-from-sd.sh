#!/usr/bin/env bash
# Stage SSH account setup on an explicitly mounted Ubuntu 20.04 Pi rootfs.
set -euo pipefail

if [[ ${EUID} -ne 0 || $# -ne 1 ]]; then
    echo "Usage: sudo bash $0 <mounted-Pi-root-partition>" >&2
    exit 2
fi

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
target_root=$(realpath -e -- "$1")
if [[ "$target_root" == / ]] || ! mountpoint -q -- "$target_root"; then
    echo "Target must be a separately mounted Pi root partition." >&2
    exit 1
fi
if [[ $(findmnt -n -o MAJ:MIN --target "$target_root") == $(findmnt -n -o MAJ:MIN --target /) ]]; then
    echo "Refusing to modify the laptop's root filesystem." >&2
    exit 1
fi
if ! grep -qx 'ID=ubuntu' "$target_root/etc/os-release" ||
   ! grep -qx 'VERSION_ID="20.04"' "$target_root/etc/os-release"; then
    echo "Target is not an Ubuntu 20.04 root filesystem." >&2
    exit 1
fi
if [[ ! -x "$target_root/usr/sbin/sshd" ]]; then
    echo "OpenSSH server is missing from the Pi image." >&2
    exit 1
fi
if ! LC_ALL=C readelf -h "$target_root/usr/sbin/sshd" | grep -Eq 'Machine:.*AArch64'; then
    echo "Target SSH server is not an ARM64 Raspberry Pi binary." >&2
    exit 1
fi

for directory in usr/local/sbin etc/systemd/system; do
    resolved=$(realpath -m -- "$target_root/$directory")
    [[ "$resolved" == "$target_root/"* ]] || {
        echo "Target path escapes the mounted Pi root: $directory" >&2
        exit 1
    }
done
if [[ -e "$target_root/usr/local/sbin/tms-firstboot-ssh-setup" ||
      -e "$target_root/etc/systemd/system/tms-firstboot-ssh-setup.service" ]]; then
    echo "SSH bootstrap is already staged; refusing to replace it." >&2
    exit 1
fi

install -D -o root -g root -m 0700 \
    "$project_root/scripts/tms-firstboot-ssh-setup.sh" \
    "$target_root/usr/local/sbin/tms-firstboot-ssh-setup"
install -D -o root -g root -m 0644 \
    "$project_root/packaging/tms-firstboot-ssh-setup.service" \
    "$target_root/etc/systemd/system/tms-firstboot-ssh-setup.service"
systemctl --root="$target_root" enable tms-firstboot-ssh-setup.service
sync
echo "Staged: next Pi boot creates tms/tms and enables password SSH on port 22."
echo "Existing account/SSH files will be backed up on the Pi before changes."
