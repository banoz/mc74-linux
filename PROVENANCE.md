# Provenance

Where every piece of this repository comes from, what it was derived from, and the
hardware findings it depends on. Upstream pins (commit hashes and sha256 sums) are in
[`sources.lock`](sources.lock).

## Authorship

All code and documentation in this repository were written by Claude (Anthropic's AI
assistant, working in Claude Code) during the MC74 bring-up in October 2026, at the request
of and directed by Vas, who ran the hardware tests on the device. Commits carry
`Author: Claude <noreply@anthropic.com>` and a `Co-Authored-By:` trailer for Vas.
Files copied unchanged from third parties are listed below and keep their original
copyright headers.

## Kernel (`kernel/`)

Base: [bcm-kona-mainline/linux](https://github.com/bcm-kona-mainline/linux), branch
`kona/7.1`, commit `546dcac3f6d7f8bcc10ddb0969a221cdf2b676b1` (Linux 7.1.0 with the
community BCM21664/BCM23550/BCM281xx work). The series in `kernel/patches/` applies on
top of that commit with `git am`. License: GPL-2.0, like the kernel.

| Patch | What | Written from / checked against |
|---|---|---|
| 0001 DTS | `bcm28155-cisco-mc74.dts`, built on the tree's `bcm11351.dtsi` | Stock MC74 firmware behaviour (dmesg, `/proc` and register dumps taken on the running stock Android), the u-boot console, and Roku's `linux-3.0.82` "ray" board files for pin/GPIO numbers |
| 0002 ESUB Ethernet | `drivers/net/ethernet/broadcom/kona_esub_eth.c` (new driver) | Register layout, DMA descriptors, Broadcom tag and PTM/MTP setup from Roku's `u-boot-2011.06` `drivers/net/bcm11140_eth.c` + `arch/arm/include/asm/arch-capri/ethHw_*.h`, and `linux-3.0.82` `drivers/net/island_net.c` (RX ring re-sync). Code is new, not copied |
| 0003 chal import | `drivers/misc/kona-caph/chal_*.c`, `include/` | **Copied byte-for-byte** from Roku's `linux-3.0.82-grsec` GPL release: `arch/arm/mach-capri/chal/{chal_caph_dma,chal_caph_cfifo,chal_caph_switch,chal_caph_intc,chal_ihf,chal_vin}.c`, `arch/arm/mach-capri/include/{chal,mach}/…`, `arch/arm/plat-kona/include/plat/…` (Broadcom copyright, GPL) |
| 0004 ALSA driver | `drivers/misc/kona-caph/kona_caph_pcm.c` (new) | Channel setup order from `linux-3.0.82` `drivers/char/broadcom/halaudio_drivers/bcm_capri/audioh/halaudio_audioh.c` and `arch/arm/mach-capri/aadmac.c`; mic front-end values from register dumps of the running stock firmware |
| 0005 simpledrm | VideoCore display mailbox support in `drivers/gpu/drm/sysfb/simpledrm.c` | Mailbox protocol from `u-boot-2011.06` `cmd_vc_display.c` / `slim_ipc_display.h`; MC74 struct offsets measured on the device |

`kernel/config/mc74_defconfig` is `savedefconfig` output of the configuration used on the
device (`bcmkona_defconfig` plus MC74 changes: appended DTB, forced command line, L2/SMC off,
built-in initramfs). `kernel/initramfs/` is new.

## Hardware findings the code depends on

These were measured on the device and are not documented elsewhere:

- **Audio clocks.** Mainline's hub CCU driver leaves the KHUB clock policy masks at values
  that only cover the clocks it knows (e.g. `0x00000623`), so AudioH/CAPH never run. The
  stock firmware has MASK1 = `0x07FFB6A7` and MASK2 = `0x1F800052` in all four policies;
  the ALSA driver ORs those in and restarts the policy engine (GO|GO_ATL). Touching
  AudioH/CAPH registers before that stalls the bus.
- **ASoC hangs** in `snd_soc_init` on this board, so the sound card is a plain ALSA driver.
- **Ethernet receive FIFO config is ESW+0x80008, not 0x80000.** With 0x80000 written, RX is
  never enabled from a clean boot, and after u-boot has enabled it the data arrives
  byte-reversed within each 64-bit word.
- **The ESUB DMA does not check descriptor ownership**: after an RX overrun the driver must
  re-sync to the oldest filled descriptor.
- **Display.** The VideoCore owns the MIPI DSI panel. u-boot (`vc run`, `vc display power on`,
  `vc display fb init`) creates an 800x1280 framebuffer at ARM 0x843f0ba0, and the VC shows a
  new frame only after an FB_UPDATE request through `display_ipc` (ARM 0x82002058, req +48,
  ack +52, doorbell bit 13 at 0x34005008). `vc display fb init` needs ~10 s after `vc run`.
- **Panel orientation.** The panel is portrait (800x1280) mounted landscape; `fbcon=rotate:3`
  is upright.
- **Touch coordinates are already landscape** (x 0..1279, y 0..799) on the cyttsp5, while the
  framebuffer is portrait: userspace must swap/invert axes rather than rotate them
  (e.g. LVGL `lv_evdev` calibration with `ROTATION_90`).
- **Mics.** "Mic1" (VRX1 SEL_MIC1B_MIC2 clear) is the handsfree mic; Mic2 is much noisier.
- **No PMU.** The bus stock uses for the PMU carries the panel bridge, backlight, ALS,
  audio jack switch, proximity sensor and LED driver instead.
- **UART** runs from a fixed ~13 MHz clock set by the bootloader; re-clocking it kills the console.

## Bootloader and partitions (`bootloader/`)

Nothing here replaces u-boot. The device keeps its stock u-boot 2011.06; only its saved
`bootcmd`/`bootdelay` change, and the kernel goes into the unused B-slot `boot2` partition.
See [`bootloader/README.md`](bootloader/README.md). The tools are new Python scripts that
drive the stock u-boot over the serial console and USB fastboot.

## Root filesystem (`rootfs/`)

Alpine Linux 3.24.2 armv7 (pinned minirootfs, packages from the official Alpine
repositories at install time), installed onto `system2` by `rootfs/install-alpine.sh`.
The scripts are new.

## Deliberately not included

- The stock firmware backup and any other Cisco/Meraki code or binaries (bootloader, VideoCore
  firmware, Android images, partition dumps).
- Credentials of any kind (Wi-Fi, Home Assistant tokens, SSH keys).
- Device-unique data: the unit's MAC address and serial number. The DT carries no
  `local-mac-address`; set it locally (see `docs/bring-up-notes.md`).
