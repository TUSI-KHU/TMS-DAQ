#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

bundle_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
running_kernel=$(uname -r)
machine=$(uname -m)
module_kernel=$(modinfo -F vermagic "$bundle_dir/bio4704.ko" | awk '{print $1}')

if [[ "$machine" != aarch64 ]]; then
  echo "This bundle is for AArch64, not $machine." >&2
  exit 1
fi

if [[ "$running_kernel" != "$module_kernel" ]]; then
  echo "Kernel mismatch: running=$running_kernel module=$module_kernel" >&2
  echo "Rebuild the modules against /lib/modules/$running_kernel/build." >&2
  exit 1
fi

module_dir="/lib/modules/$running_kernel/kernel/drivers/daqnavi"
install -d -m 0755 "$module_dir"
install -m 0644 "$bundle_dir/biokernbase.ko" "$module_dir/biokernbase.ko"
install -m 0644 "$bundle_dir/bio4704.ko" "$module_dir/bio4704.ko"
install -m 0644 "$bundle_dir/71-advantech-usb4704.rules" /etc/udev/rules.d/71-advantech-usb4704.rules

printf 'biokernbase\nbio4704\n' > /etc/modules-load.d/advantech-usb4704.conf
depmod -a "$running_kernel"
udevadm control --reload-rules
udevadm trigger --subsystem-match=daq || true
modprobe biokernbase
modprobe bio4704

echo "Installed USB-4704 modules for $running_kernel"
echo "Connect the device, then inspect: dmesg; ls -l /dev/daq*; cat /sys/class/daq/daq0/desc"

