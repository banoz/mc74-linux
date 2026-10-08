# MC74 bring-up notes

Chronological lab notes from the bring-up (October 2026), lightly edited for publication:
the unit serial, MAC address and local backup paths are removed. File names refer to the
original working directory; the maintained versions of the scripts are in this repository.
For the hardware findings in short, see [PROVENANCE.md](../PROVENANCE.md).

# MC74 kernel build: first bring-up image

Nothing in this directory has been flashed or sent to a device.

## Images (`images/`)

| File | What it is |
|---|---|
| `zImage` | Linux 3.0.82-grsec, ray board, RAM base 0xA0000000, built-in initramfs |
| `uImage` | `zImage` wrapped by mkimage, load/entry 0xA0008000 (for `bootm`) |
| `boot-mc74.img` | Android boot.img v0 using the stock boot.img addresses (kernel 0xa0008000, tags 0xa0000100, page 2048), for `fastboot boot` (runs from RAM, writes nothing) |
| `ramdisk.cpio.gz` | The same tiny `/init` as the built-in initramfs, because boot.img needs a ramdisk |
| `config-3.0.82-mc74` | The `.config` used |

Version string: `Linux version 3.0.82-grsec (user@YOOPC) (gcc version 5.4.0 (Buildroot 2017.05)) #1 SMP PREEMPT`

## What it does when booted

`/init` (`initramfs/init.c`) does not use libc. It mounts only proc, sysfs and devtmpfs and
never mounts the eMMC. It prints cmdline, cpuinfo, meminfo and partitions on ttyS0, then
offers a small read-only prompt: `cat <file>`, `ls <dir>`, `dmesg`, `reboot`.

## Toolchain

Bootlin `armv7-eabihf--glibc--stable-2017.05-toolchains-1-1` (gcc 5.4.0, Buildroot 2017.05).
It is in `../toolchains/` and matches its published sha256. Its glibc needs kernel 3.10 or
newer, so userspace for this 3.0 kernel must be static and libc-free (as `/init` is), or use a
different libc.

`mkimage` is built from `../roku-oss/u-boot-2011.06` (`uboot-tools/tools/mkimage`).

## How it was built

```
export PATH=$HOME/Documents/MC74/toolchains/armv7-eabihf--glibc--stable/bin:$PATH
cd ~/Documents/MC74/roku-oss/linux-3.0.82-grsec
M="make O=$HOME/Documents/MC74/build-output/obj ARCH=arm CROSS_COMPILE=arm-linux- KCFLAGS=-std=gnu89"
$M bcm11130_ray_mxc_defconfig
# then: BCM_RAM_BASE=0xA0000000, OPROFILE off, BLK_DEV_INITRD on,
#       INITRAMFS_SOURCE=initramfs/initramfs.list, CMDLINE="console=ttyS0,115200n8 mem=510M rdinit=/init"
$M -j4 zImage modules
```

Fixes needed for gcc 5 on this 3.0 tree:
- `KCFLAGS=-std=gnu89`: gcc 5 defaults to gnu11, which changes the meaning of `extern inline`
  (multiple definitions of `return_address`, `__STDC_VERSION__` redefinitions). Upstream fixed
  this the same way.
- `CONFIG_OPROFILE` off: `arch/arm/oprofile` does not match this tree's perf API.
- `patches/0001-vchiq_arm-drop-inline-on-extern-functions-for-gcc5.patch`: this is the only
  source edit, and it is already applied in the tree.

## Known limits

- The stock MC74 board is `CONFIG_MACH_CAPRI_ME1`, which is not in the Roku tree (see
  `stock/config-3.0.31`). Ray pinmux and GPIOs may not match the MC74.
- No framebuffer driver is enabled yet. Linux 3.0 has no `simple-framebuffer` (it arrived in
  3.10 and needs DT), so display needs the vendor fb driver.
- The 8 modules built (audio/csx test drivers, scsi_wait_scan) are not needed for bring-up.

## Update 2026-10-06: first boot to userspace (RAM only, nothing flashed)

`images/uImage-first-userspace` (ramtest9, config in `images/config-ramtest9-first-userspace`)
boots from RAM and reaches the `/init` prompt `mc74#` on ttyS0. Both
CPUs come up and 510 MB of RAM is visible.

### How to RAM-boot it (about 1 s over USB)

- `usbboot.py <uImage> <log>`: catches u-boot on serial, sets a RAM-only `bootcmd=bootm
  90000000` (never saveenv), runs `fastboot`, then `fastboot stage <uImage>` and
  `fastboot continue`. The fastboot download buffer is at 0x90000000.
- `ramboot.py` does the same over serial YMODEM (`loady`). It takes about 6 min and is
  unreliable.
- If fastboot never enumerates on USB, replug the MC74's USB cable.

### Fixes needed to get here (in order)

1. **ATAG pointer**: bootm passes 0x90000100, outside RAM. See `patches/0002`.
2. **`l2off`**: enabling L2 goes through a secure-monitor call (SMC), which crashes.
3. **UART clock**: the MC74 uartb clock is about 12.9 MHz (divisor 7 at 115200), not 26 MHz.
   The Kona 8250 `clk_set_rate()` re-clocked the live console UART, after which output
   stopped. The fix keeps the bootloader's clock and derives uartclk from the divisor
   (`patches/0003`, which also still contains MC74DBG markers).
4. **`CONFIG_BCM_OTP` off**: the secretkey driver's SMC returns with r4-r6/lr zeroed, so the
   secure monitor ABI differs from Roku's. Stock also has OTP off.
5. **`CONFIG_CAPRI_DORMANT_MODE` off**: the idle path makes SMCs.
6. **VideoCore drivers off** (`BCM_VC_*`, `KONA_VCHIQ`): bootm does not start VideoCore or
   pass the dt-blob, so vc_mem aborts.

### Known gaps

- eMMC: "unrecognised EXT_CSD structure version 7". The 3.0 MMC core is too old for this
  eMMC, so it cannot be read or written (safe for testing).
- Display and VideoCore need the `android`-style VC boot plus the dt-blob tag.
- Secure monitor calls need the MC74 (Mobicore) calling convention.
- Pinmux is ray, not ME1: "Invalid DT-Pinmux", and tft_panel has a GPIO 7 conflict.

## Update 2026-10-06 (later): Linux 7.1 boots on the MC74 (RAM only, nothing flashed)

`mainline/uImage-mainline-1` is built from github.com/bcm-kona-mainline/linux
(commit in `mainline/bcm-kona-mainline.commit`, Linux 7.1) with host gcc 13
(arm-linux-gnueabihf), the new DT `mainline/bcm28155-cisco-mc74.dts` appended, and the same
libc-free `/init`. It is RAM-booted with `usbboot.py`.

Result: it reaches `mc74#` in about 1.6 s with both CPUs, 496 MB, and the ttyS0 console
(dw-apb-uart, fixed 13 MHz clock). **The eMMC works**: mmcblk0 (M62704, 3.53 GiB) with all
24 GPT partitions, boot0/boot1 and RPMB are detected, and nothing mounts it.

DT choices for the first boot:
- memory 0xa0000000 + 510 MB
- UART clock as a fixed-clock
- eMMC on sdio2 (8-bit)
- L2, SMC and watchdog disabled
- no PMU/regulators

Config: bcmkona_defconfig with ARCH_BCM_MOBILE_L2_CACHE/SMC off, ARM_ATAG_DTB_COMPAT off (so
u-boot's out-of-RAM ATAG pointer is ignored), APPENDED_DTB, and our CMDLINE forced.

The kernel log still shows "slave_ccu ... error initializing gate for bsc3" (harmless for now).

Build:
```
cd ~/Documents/MC74/mainline/bcm-kona-mainline
make O=../build-mc74 ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j4 zImage dtbs
cat ../build-mc74/arch/arm/boot/zImage ../build-mc74/arch/arm/boot/dts/broadcom/bcm28155-cisco-mc74.dtb > zImage-dtb
mkimage -A arm -O linux -T kernel -C none -a 0xA0008000 -e 0xA0008000 -n "MC74 Linux" -d zImage-dtb uImage
```

### Busybox userspace (2026-10-06)

`mainline/uImage-mainline-busybox` is the same Linux 7.1 kernel and DT with a static
BusyBox 1.38.0 initramfs (`busybox-initramfs/`: `init` script, `initramfs.list`, `profile`).
It boots to a `mc74:~#` login shell on ttyS0 that respawns if it exits.

`/init` mounts only proc, sysfs, devtmpfs, devpts, tmpfs and debugfs. It never mounts the eMMC.
To look at an eMMC filesystem, use `mount -o ro,noload` for ext4, so the journal is not
replayed (a plain `ro` mount can still write).

BusyBox was built from busybox.net's 1.38.0 tarball (sha256 verified) with `make defconfig`,
then `CONFIG_STATIC=y` and `CONFIG_TC` off, using arm-linux-gnueabihf- gcc 13.

### Wi-Fi (2026-10-06)

`mainline/uImage-mainline-wifi2` runs the BCM4339 through mainline brcmfmac on SDIO1:
- WLAN_REG_ON is GPIO 90, handled by mmc-pwrseq-simple.
- The firmware is the stock `fw_wifi.bin` v6.37.37 plus `fw_wifi_nvram.txt`, installed as
  `brcm/brcmfmac4339-sdio.{bin,txt}` (originals in `<stock backup>/wifi/`).
- `wlan0` comes up and `iw dev wlan0 scan` works.

The initramfs also has static `iw` 6.17, `wpa_supplicant`/`wpa_cli` 2.12 (nl80211, internal
crypto, WPA2-PSK, no SAE/WPA3) built against libnl 3.12 (sources in `mainline/wifi-src/`),
and `/usr/sbin/wifi-up`. `wifi-up` sets the MAC, then either scans
(no credentials) or runs wpa_supplicant + udhcpc using `/etc/wifi-credentials.conf`. That file
is built from `~/Documents/MC74/wifi-credentials.conf` if it exists, and is never committed or
printed.

The eMMC stays `mmcblk0` thanks to the DT aliases mmc0=sdio2, mmc1=sdio1.

### PMU / regulators (2026-10-06): there is no PMU

- Stock MC74 has no regulator or PMU support at all: no CONFIG_REGULATOR, no MFD driver, no
  /sys/class/regulator.
- The bootloader's PMU accesses all fail on every boot ("UNIDENTIFIED PMU", error 3 = NAK).
- A read-only `i2cdetect -r` from Linux 7.1 finds **nothing at 0x08/0x0c** (where a BCM590xx
  would answer) on the PMU BSC (0x3500d000). That bus instead carries the stock "i2c-2"
  peripherals:
  - 0x0e panel (innolux)
  - 0x10 cm3232
  - 0x17 mp3309 backlight
  - 0x3b ts3a227e
  - 0x60 CM36283
  - 0x62 pca9632 LEDs
- So the MC74 (PoE, no battery) uses discrete or always-on supplies. The "regulators" left to
  model are plain GPIO enables (e.g. LCD power GPIO 4, backlight 7, USB host power 43).
- bsc1/bsc2 are empty. bsc3 can't be used yet because mainline can't ungate its clock
  (slave_ccu 0x0484 bit 18); the touch controller (stock 0x24) is probably on it.

### Display (2026-10-07): Linux console on the MC74 panel

The VideoCore owns the display (MIPI DSI -> TC358778 -> panel). u-boot can start it and ask it
for an ARM-writable framebuffer (`tools/display-prep.txt`):
- `vc run` starts the VC.
- `vc display power on` powers the display.
- `vc display fb init` replies 800x1280, pitch 3200, RGBA32 (bytes R,G,B,A; a red fill test
  confirmed it), double buffer at VC 0xc43f0ba0 / 0xc47d8bc0 = ARM 0x843f0ba0 / 0x847d8bc0.
- `vc display fb update 0` shows buffer 0.
- Don't run `vc display fb pattern`: it sends FB_TERM, and the VC falls back to its splash.

After that, `usbboot.py mainline/uImage-mainline-display <log> --no-catch` boots Linux 7.1. The
DT has a `simple-framebuffer` at 0x843f0ba0 (x8b8g8r8, 800x1280, stride 3200) under /chosen,
and with console=tty0, simpledrm gives /dev/fb0 and fbcon (100x80 text) on the panel.

How the display protocol works: a request struct at VC symbol `display_ipc`, IPC doorbell event
0xd, then poll `ack` (u-boot `cmd_vc_display.c`, `slim_ipc_display.h`). Also useful: `vc log msg`
prints the VC firmware log.

### Display fixes and touchscreen (2026-10-07)

Display, as of `mainline/uImage-mainline-display5` / `-touch2`:
- **Alpha**: the VC framebuffer is RGBA with real alpha, so the DT format must be `a8b8g8r8`
  (simpledrm then writes opaque pixels). With `x8b8g8r8` the panel stays black.
- **Refresh**: the VC only shows new content after a display_ipc FB_UPDATE. `/init` starts
  `vc-fb-refresh` (source `busybox-initramfs/vcfb/vc-fb-refresh.c`) when 0x82002070 reads 800.
  It sends FB_UPDATE(0) every 100 ms via mailbox 0x82002058 (MC74 layout: req @+48, ack @+52)
  and doorbell `1<<13` -> 0x34005008.
- **Timing**: wait about 10 s after `vc run` before `vc display fb init`, otherwise "Timedout
  waiting for response on request 3". `usbboot.py --display` handles this.
- The panel is mounted landscape on an 800x1280 portrait framebuffer. `fbcon=rotate:3` (owner confirmed upright text) plus
  CONFIG_FRAMEBUFFER_CONSOLE_ROTATION; it can be changed live via
  /sys/class/graphics/fbcon/rotate_all.

Touchscreen: Cypress/Parade CYTMA448 (TrueTouch Gen5), mainline `cyttsp5`
(compatible `cypress,tt21000`):
- It is on **BSC1 (i2c-0, 0x3e016000) at 0x24**; vendor bsc-i2c.0 = BSC1, bsc-i2c.2 = PMU_BSC.
- Reset is GPIO 103, active-low. u-boot leaves it low, which is why the first scan found
  nothing.
- IRQ is GPIO 102, **IRQ_TYPE_EDGE_FALLING**, because Kona GPIO has no level IRQs (level ->
  -EINVAL).
- vdd-supply is a fixed 3.3 V regulator (no PMU).
- Result: `input: cyttsp5 ... input0`. Events arrive; touch coordinates are landscape,
  X 0..~1279, Y 0..~799.

### Audio (2026-10-07): speakerphone tone from Linux 7.1

`mainline/uImage-mainline-audio5`: `drivers/misc/kona-caph/` (copy in `mainline/kona-caph/`) =
Broadcom's GPL chal register helpers (CAPH DMA/CFIFO/switch/intc, AudioH IHF), vendored
unchanged, plus `kona_caph_test.c`. Writing 1 to `/sys/kernel/debug/kona_caph_test/play` plays
a 1 kHz tone on the handsfree speaker; the owner confirmed a clean beep.

- Chain: DDR ring (2x960 B halves, 48 kHz S16 stereo) -> AADMAC ch -> CFIFO (1024 B, thres 4/0)
  -> SSASW (trigger CAPH_IHF_THR_MET, MONO_16BIT) -> AudioH IHF FIFO 0x35025000 -> IHF DAC.
  The order follows halaudio (init / prepare / enable). Halves are re-armed from a 1 ms hrtimer
  (no IRQ yet).
- **Clocks**: mainline's hub CCU driver drops AudioH/CAPH from the KHUB policy masks. The
  driver ORs in stock's MASK1=0x07FFB6A7 / MASK2=0x1F800052 (policies 0-3), runs GO|GO_ATL,
  then sets AUDIOH gate low16=0xffff and CAPH low16=0x3030. Status then reads
  0x0055FFFF/0x00103030, the same as stock. Touching AudioH/CAPH before this hangs the bus.
- The Linux ASoC core (`snd_soc_init`) hangs on this board, so ASoC is off and the code lives in
  drivers/misc.
- The stock register capture (idle vs playing) and the KHUB dumps are in
  `<stock backup>/audio/`.

## Update 2026-10-07: ALSA sound card (RAM only, nothing flashed)

`uImage-mainline-alsa2` (= `uImage-mainline-latest`). The CAPH tone test became a plain ALSA
driver, `drivers/misc/kona-caph/kona_caph_pcm.c` (compatible `brcm,kona-caph`; ASoC still hangs
on this board, so no ASoC).
- Card 0 "MC74", device 0: playback 48 kHz S16_LE stereo to the handsfree speaker (IHF), capture
  48 kHz S16_LE mono from the analog mic (AudioH VIN right, VRX PGA). Two periods (the AADMAC
  ring is two halves), period 20 ms .. 32 KB; the ring flags are polled by an hrtimer (HZ=100).
- Mixer: `Speaker Playback Switch` (DAC mute; the IHF path keeps running because it paces the
  DMA), `Mic Capture Volume` 0..63 (VRX1 gain, stock 37), `Mic Capture Source` Mic1/Mic2 (VRX1
  SEL_MIC1B_MIC2, stock = Mic2).
- Mic front end follows the stock running state: VRX1=0x00250040, VREF=0x2, VMIC=0x32,
  ADC_CTL AMIC_EN. The ACI/AUXMIC block (0x3500e000) is not touched (its APB clock state is
  unknown; a gated access would stall the bus).
- Verified: 3 s playback takes 3.08 s, 3 s capture takes 3.02 s, full duplex works; captured data
  is a live signal around DC ~1900. Audible test with the tone still pending (owner must be present).
- Userspace: static alsa-lib/alsa-utils 1.2.14 (`aplay`, `arecord`, `amixer`) + /usr/share/alsa,
  test tone `/root/tone-2s.wav`. Silent test: `aplay -D hw:0 -t raw -f S16_LE -r 48000 -c 2 -d 3 /dev/zero`.
- Note: busybox `reboot` does nothing (PID 1 is the init script); use `reboot -f`.

## Update 2026-10-07: Ethernet receive fixed (RAM only, nothing flashed)

`uImage-mainline-eth9` (= `uImage-mainline-latest`, includes the ALSA card). Root cause: the
driver wrote the PTM (receive FIFO) config to ESW+0x80000, but u-boot's `ethHw_regPtmConfig` is
ESW+**0x80008**. From a clean boot the receive FIFO was therefore never enabled (RX=0); after
u-boot's `dhcp` it was enabled by u-boot, but my write to 0x80000 made received data arrive
byte-reversed within each 64-bit word (DHCP offers were received but unparseable). With the
offset fixed: clean-boot `udhcpc` gets 192.168.11.100, 1400-byte pings to 8.8.8.8 have 0% loss,
a 10 MB HTTP download takes 12 s (~7 Mbit/s; RX is polled every 2 ms, no IRQ yet), no RX errors.

## Update 2026-10-07: in-kernel VideoCore refresh (RAM only, nothing flashed)

`uImage-mainline-disp1` (= latest; includes ALSA + Ethernet fix). simpledrm got an optional DT
property `brcm,vc-display-ipc = <0x82002058 0x34005008>` on the simple-framebuffer node: after
every plane update it queues one FB_UPDATE to the VC display_ipc mailbox (+0 cmd 4, +48 req,
+52 ack; doorbell BIT(13) to IPC ASET) and waits up to ~100 ms for the ack, which also paces
updates. `/init` no longer starts the userspace `vc-fb-refresh` poller. Verified: req/ack counters
advance together (fbcon cursor blink), /dev/fb0 is XRGB8888 800x1280.
A colour/orientation test image written to /dev/fb0 (with fbcon unbound) shows upright when
rotated CCW like fbcon=rotate:3. Boot with `usbboot.py ... --display`.

Audible test 2026-10-07 (owner present): 2 s 1 kHz tone while recording. Mic1: noise rms ~50,
tone amplitude ~28800 (near full scale at gain 37) -> the handsfree mic next to the speaker.
Mic2: noise rms ~720, tone amplitude ~410. Default `Mic Capture Source` is now Mic1
(`uImage-mainline-disp2`).

## Update 2026-10-07: Alpine Linux on the eMMC (system2), kernel still RAM-booted

Owner approved formatting `system2` (mmcblk0p18, inactive B slot; u-boot uses "first set of
partition images" = slot A). `rootfs/install-alpine.sh` (run from the initramfs shell over
Ethernet) made it ext4 `mc74root` and installed Alpine 3.24.2 armv7 + openrc, alsa-utils, iw,
wpa_supplicant, dropbear, chrony, python3/pip (~70 MB of 464 MB); `rootfs/configure-alpine.sh`
set fstab, eth0 DHCP, ttyS0 root shell (no login, bench device), firmware, services;
`rootfs/fix-console.sh` fixed inittab (Alpine ships a commented ttyS0 line), chronyd `-F 0` (no
seccomp), swclock instead of hwclock.
Boot: `uImage-mainline-alpine1` (= latest). The initramfs `/init` waits 3 s on the serial
console (press Enter to stay in the busybox shell for maintenance), otherwise mounts system2 and
`switch_root`s to Alpine's /sbin/init. Slot A (stock Android), u-boot, VC firmware, recovery,
cache and userdata are untouched.
Owner confirmed 2026-10-07: the test image on the panel is upright landscape with correct colours
(XRGB8888 via /dev/fb0, rotated CCW).

## Update 2026-10-07: the MC74 boots Alpine on its own (owner-approved writes)

- `boot2` (mmcblk0p16, block 0x24000) holds `uImage-mainline-emmc1` (6.8 MB: slim initramfs =
  busybox + /init that switch_roots to system2). Written from u-boot RAM by
  `tools/flash_boot2.py` (fastboot stage + temporary bootcmd `mmc write`), md5 verified from Linux.
- Saved u-boot env (backups of u-boot, u-boot2, u-boot-env, u-boot-env2 in
  `<stock backup>/uboot/`, md5 verified) now has bootdelay=3 and
  bootcmd = stock panel/MIPI init; MUTE -> `android recovery`; VOL_DOWN -> `fastboot`; else
  `vc run; sleep 12; vc display power on; vc display fb init; vc display fb update 0;
  gpt setenv boot2; mmc dev 0; mmc read 90000000 ${gpt_partition_addr} 4000; bootm 90000000;
  android` (stock Android as fallback).
- Original bootcmd: `gpio set 95; gpio set 6; gpio set 96; i2c mw 17 0 fc; mipi init; if key MUTE;
  then android recovery; fi; if key VOL_DOWN; then fastboot; else android; fi;` (bootdelay=1).
- To boot stock once: stop autoboot, type `android`. USB RAM boots still work (usbboot.py catches
  the 3 s prompt).

## Touch coordinates

The cyttsp5 reports landscape coordinates (x 0..1279, y 0..799, measured by tapping the
corners) although the framebuffer is 800x1280 portrait, so userspace has to swap/invert axes
rather than rotate them (owner-confirmed with a test app).

## Setting the MAC address locally

The DT in this repository has no `local-mac-address` (it is unit-unique). Without one the ESUB
driver picks a random address at each boot. To keep a stable address, either add
`local-mac-address = [xx xx xx xx xx xx];` to the `ethernet@38200000` node in a local copy of
the DTS (the stock value is the u-boot `ethaddr` / Android `bcmmac`), or set it in Alpine's
`/etc/network/interfaces`:

```
auto eth0
iface eth0 inet dhcp
	hwaddress ether xx:xx:xx:xx:xx:xx
```
