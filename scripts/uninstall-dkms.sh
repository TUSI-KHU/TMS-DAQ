#!/usr/bin/env bash
set -euo pipefail

package_name=advantech-usb4704
package_version=20260306
source_dir="/usr/src/$package_name-$package_version"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

modprobe -r bio4704 2>/dev/null || true
modprobe -r biokernbase 2>/dev/null || true
dkms remove -m "$package_name" -v "$package_version" --all
rm -f /etc/udev/rules.d/71-advantech-usb4704.rules
rm -f /etc/modules-load.d/advantech-usb4704.conf

if [[ -d "$source_dir" ]]; then
  rm -rf -- "$source_dir"
fi

udevadm control --reload-rules
depmod -a
echo "Removed $package_name/$package_version."

