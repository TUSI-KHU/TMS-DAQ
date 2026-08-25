#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
tool_root="${USB4704_TOOLCHAIN_ROOT:-/tmp/usb4704-jammy-cross-toolchain-$(id -u)/aarch64-linux-gnu}"
package_dir="$repo_root/build/cache/jammy-cross-toolchain-packages"
archive_url=https://archive.ubuntu.com/ubuntu

gcc_bin="$tool_root/usr/bin/aarch64-linux-gnu-gcc-11"
if [[ -x "$gcc_bin" ]]; then
  printf '%s\n' "$tool_root"
  exit 0
fi

for command_name in curl dpkg-deb sha256sum; do
  command -v "$command_name" >/dev/null || {
    echo "Required command not found: $command_name" >&2
    exit 1
  }
done

# Ubuntu 22.04 packages matching the compiler recorded in the Jammy raspi
# kernel headers: GCC 11.4.0. Packages and hashes come from the official
# jammy-updates amd64 Packages index.
packages=(
  'gcc-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb|aa7ad168a8404a22f7bc31d137be2336644b3cbc99174518da443dfe88d51411|pool/main/g/gcc-11-cross/gcc-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb'
  'cpp-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb|b1ccd3108ea2191519b988826631e148d99fb5c0e9e9264bd8370ceacc51e111|pool/main/g/gcc-11-cross/cpp-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb'
  'gcc-11-aarch64-linux-gnu-base_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb|5e2180045a16c4730f977265e44c46f2afcf847f3fa991e799f84217132eab99|pool/main/g/gcc-11-cross/gcc-11-aarch64-linux-gnu-base_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb'
  'libgcc-11-dev-arm64-cross_11.4.0-1ubuntu1~22.04.3cross1_all.deb|bc16d649bfdfdb7fe505ec9ef9853463f4f379dad5459cffa3ff5cdf477c817e|pool/main/g/gcc-11-cross/libgcc-11-dev-arm64-cross_11.4.0-1ubuntu1~22.04.3cross1_all.deb'
)

mkdir -p "$tool_root" "$package_dir"

for package in "${packages[@]}"; do
  IFS='|' read -r filename expected_sha url_path <<< "$package"
  package_path="$package_dir/$filename"

  if [[ ! -f "$package_path" ]]; then
    echo "Downloading Jammy toolchain package: $filename" >&2
    curl --fail --location --retry 3 --output "$package_path" "$archive_url/$url_path"
  fi

  printf '%s  %s\n' "$expected_sha" "$package_path" | sha256sum --check - >&2
  dpkg-deb --extract "$package_path" "$tool_root"
done

test -x "$gcc_bin"
"$gcc_bin" --version >&2

printf '%s\n' "$tool_root"
