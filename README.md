# Linux on the Cisco Meraki MC74

Mainline-based Linux (7.1) for the Cisco Meraki MC74 desk phone: Broadcom BCM28155/BCM11130
"Capri" (Cortex-A9), 10" 1280x800 touchscreen, speakerphone, PoE Ethernet, BCM4339 Wi-Fi.
The device boots by itself into Alpine Linux. This repository covers the Linux side only
(kernel, boot setup, root filesystem); applications are kept elsewhere.

## Status

| Area | State |
|---|---|
| Boot | stock u-boot loads this kernel from `boot2`, which switches to Alpine on `system2`; stock Android stays as fallback |
| Console | UART (115200) and framebuffer console |
| Storage | eMMC |
| Display | VideoCore-owned panel through simpledrm + in-kernel FB_UPDATE mailbox |
| Touch | cyttsp5 (tt21000) |
| Ethernet | ESUB switch driver: DHCP, ~7 Mbit/s (RX polled) |
| Wi-Fi | BCM4339 brcmfmac (stock firmware, not included) scans; WPA2 tools present |
| Audio | ALSA card: speaker playback, analog mic capture |
| Not yet | VideoCore start from Linux, Ethernet RX interrupts, echo cancellation, earpiece/handset |

## Layout

```
kernel/patches/     patch series for bcm-kona-mainline kona/7.1 @546dcac3f (git am)
kernel/config/      mc74_defconfig
kernel/initramfs/   slim initramfs: busybox + /init that switch_roots to system2
busybox/            busybox 1.38.0 config (static)
bootloader/         partition layout, u-boot bootcmd, serial/fastboot tools
rootfs/             Alpine 3.24 install/config scripts
docs/               bring-up notes
scripts/            fetch-sources.sh, build-kernel.sh
sources.lock        upstream pins (commit / sha256)
PROVENANCE.md       where everything comes from, and the hardware findings
```

## Build

On Ubuntu 24.04 (`gcc-arm-linux-gnueabihf`, `u-boot-tools`, `git`, `curl`, `flex`, `bison`,
`bc`, `libssl-dev`):

```
scripts/fetch-sources.sh     # pinned kernel and busybox into ./src
scripts/build-kernel.sh      # -> out/uImage-mc74 (fits the 8 MB boot2)
```

## Install (summary)

1. Test without flashing: `bootloader/tools/usbboot.py out/uImage-mc74 boot.log --display`.
2. From the RAM-booted shell (press Enter during the 3 s prompt), install Alpine onto `system2`
   with `rootfs/install-alpine.sh` and `rootfs/configure-alpine.sh` (needs Ethernet).
3. Write the kernel into `boot2` with `bootloader/tools/flash_boot2.py`, then save the new
   `bootcmd` ([bootloader/README.md](bootloader/README.md)).

Writing `boot2`, `system2` and the u-boot environment replaces data on the device. Take a full
backup of the eMMC partitions first; this repository contains none of the stock firmware.

## License

GPL-2.0 (see `LICENSE`). Files imported from Broadcom/Roku keep their original headers.
