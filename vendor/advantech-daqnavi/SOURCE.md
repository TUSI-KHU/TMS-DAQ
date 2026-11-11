# Advantech source provenance

- Product: DAQNavi Driver for Linux
- Advantech document: `1-LXHFQJ`
- Vendor release: `DAQ_Linux_20260306_64bit.run`
- Published: 2026-03-30
- Download: <https://downloadt.advantech.com/download/downloadsr.aspx?File_Id=1-34WAGV8>
- Download SHA-256: `251e1b7ecdfb2cbc51a7b9e65f395969cc95abac07468f3fa06852cb09e6df4a`

Only the kernel source and its required headers are retained here:

- `drivers/driver_lib`: `biokernbase.ko`
- `drivers/usb4702_usb4704`: `bio4704.ko`
- `drivers/inc`: shared kernel/API headers

The vendor modules declare `MODULE_LICENSE("GPL")`. The original package's
x86-64 user-space libraries and daemons are not copied because they cannot run
on AArch64 and their source is not included in the vendor package.

## Maintained local compatibility changes

Reviewed: 2026-11-11. The original download hash above identifies the vendor
installer; it is not the hash of the locally modified source tree.

The local source includes build-path handling (`$(CURDIR)` for recursive
Kbuild), Linux kernel compatibility and buffered-input lifecycle fixes.
The optional `GET_USB_FLAG` request is rate-limited and disabled after STALL
on incompatible firmware; host-side overrun/index checks remain active.
These are functional compatibility changes, not only build-file edits.

Current operation uses Ubuntu 22.04 x86_64 / kernel `6.8.0-138-generic` with
GCC 12 and DKMS. Raspberry Pi ARM64 support and earlier verification are
retained. The TMS application uses its native ioctl/mmap wrapper rather than
the proprietary DAQNavi user-space libraries.

See [driver status](../../docs/usb4704-porting-status.md) and
[current deployment](../../docs/current-deployment.md) for tested scope,
remaining hardware checks and the architecture-specific installation paths.
