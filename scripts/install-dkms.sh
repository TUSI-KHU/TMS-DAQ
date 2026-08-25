#!/usr/bin/env bash
set -euo pipefail

package_name=advantech-usb4704
package_version=20260306
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
source_dir="/usr/src/$package_name-$package_version"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if [[ $(uname -m) != aarch64 ]]; then
  echo "DKMS installation must run on the AArch64 target." >&2
  exit 1
fi

for command_name in dkms make gcc; do
  command -v "$command_name" >/dev/null || {
    echo "Required command not found: $command_name" >&2
    echo "Install prerequisites: apt install dkms build-essential linux-headers-$(uname -r)" >&2
    exit 1
  }
done

test -d "/lib/modules/$(uname -r)/build" || {
  echo "Missing headers for $(uname -r)." >&2
  echo "Install: apt install linux-headers-$(uname -r)" >&2
  exit 1
}

if [[ -e "$source_dir" ]]; then
  echo "Refusing to replace existing DKMS source: $source_dir" >&2
  echo "Remove the existing $package_name/$package_version installation first." >&2
  exit 1
fi

install -d -m 0755 "$source_dir"
install -m 0644 "$repo_root/Makefile" "$source_dir/Makefile"
cp -a "$repo_root/vendor" "$source_dir/vendor"
install -m 0644 "$repo_root/packaging/dkms.conf" "$source_dir/dkms.conf"

dkms add -m "$package_name" -v "$package_version"
dkms build -m "$package_name" -v "$package_version" -k "$(uname -r)"
dkms install -m "$package_name" -v "$package_version" -k "$(uname -r)"

install -m 0644 "$repo_root/packaging/71-advantech-usb4704.rules" /etc/udev/rules.d/71-advantech-usb4704.rules
printf 'biokernbase\nbio4704\n' > /etc/modules-load.d/advantech-usb4704.conf
depmod -a
udevadm control --reload-rules
modprobe biokernbase
modprobe bio4704

echo "Installed $package_name/$package_version with DKMS for $(uname -r)."

