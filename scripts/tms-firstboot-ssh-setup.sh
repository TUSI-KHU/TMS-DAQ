#!/usr/bin/env bash
# Runs once as root on the Pi; installed by provision-pi-ssh-from-sd.sh.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ ${EUID} -eq 0 ]] || exit 1
if [[ $(uname -m) != aarch64 ]] ||
   ! grep -qx 'ID=ubuntu' /etc/os-release ||
   ! grep -qx 'VERSION_ID="20.04"' /etc/os-release; then
    echo "This bootstrap is only for Ubuntu 20.04 ARM64 on the Pi." >&2
    exit 1
fi

backup_dir=$(mktemp -d /var/backups/tms-ssh-setup.XXXXXX)
chmod 0700 "$backup_dir"
for name in passwd shadow group gshadow; do
    cp -a "/etc/$name" "$backup_dir/"
done
cp -a /etc/ssh "$backup_dir/ssh"
echo "Account and SSH backups: $backup_dir"

if ! id tms >/dev/null 2>&1; then
    useradd --create-home --user-group --shell /bin/bash tms
elif (( $(id -u tms) < 1000 )); then
    echo "Refusing to repurpose an existing system account named tms." >&2
    exit 1
fi
usermod --shell /bin/bash tms
printf 'tms:tms\n' | chpasswd
for group in sudo plugdev dialout; do
    if getent group "$group" >/dev/null; then
        usermod -a -G "$group" tms
    fi
done

install -d -m 0755 /etc/ssh/sshd_config.d
# Focal images can differ in whether the drop-in directory is included.
# Put it first, since sshd uses the first global value it reads.
sed -i '1iInclude /etc/ssh/sshd_config.d/*.conf' /etc/ssh/sshd_config
printf '%s\n' \
    '# TUSI field login; configured by the one-time SD recovery.' \
    'Port 22' \
    'PasswordAuthentication yes' \
    'PubkeyAuthentication yes' \
    'AuthenticationMethods any' \
    > /etc/ssh/sshd_config.d/00-tms-field.conf
ssh-keygen -A
install -d -m 0755 /run/sshd
/usr/sbin/sshd -t
systemctl enable ssh.service
systemctl restart ssh.service
systemctl is-active --quiet ssh.service
systemctl disable tms-firstboot-ssh-setup.service
echo "SSH READY: tms@10.47.0.2 port 22, password tms"
