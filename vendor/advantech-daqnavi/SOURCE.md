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

Local build-only change: the two vendor makefiles use `$(CURDIR)` instead of
the inherited `$(PWD)` when passing the external module path to Kbuild. This
does not change driver behavior; it fixes recursive `make -C` builds.
