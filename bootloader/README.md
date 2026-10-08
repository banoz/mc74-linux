# Booting the MC74

The MC74 keeps its stock u-boot 2011.06 (Broadcom fork). This repo never replaces u-boot; it
uses the stock A/B partition layout and changes only the saved `bootcmd` and `bootdelay`.

## Partition layout used

The eMMC (GPT) holds two firmware sets. u-boot prints `Using first set of partition images`,
so stock Android runs from slot A; slot B is free.

| Partition | Device | Size | Use |
|---|---|---|---|
| `boot` | mmcblk0p15 | 8 MB | stock Android kernel (unchanged, fallback) |
| `boot2` | mmcblk0p16 | 8 MB | **this kernel** (`uImage`, ≤ 8 MB) |
| `system` | mmcblk0p17 | 506 MB | stock Android system (unchanged) |
| `system2` | mmcblk0p18 | 506 MB | **Alpine root**, ext4 label `mc74root` |
| u-boot, u-boot-env, vc-firmware, dt-blob, recovery, cache, userdata | | | unchanged |

`boot2` starts at eMMC block `0x24000`; u-boot finds it with `gpt setenv boot2`.

## Boot command

Stock:

```
gpio set 95; gpio set 6; gpio set 96; i2c mw 17 0 fc; mipi init; if key MUTE; then android recovery; fi; if key VOL_DOWN; then fastboot; else android; fi;
```
with `bootdelay=1`.

MC74 Linux (`bootdelay=3`):

```
gpio set 95; gpio set 6; gpio set 96; i2c mw 17 0 fc; mipi init; if key MUTE; then android recovery; fi; if key VOL_DOWN; then fastboot; fi; vc run; sleep 12; vc display power on; vc display fb init; vc display fb update 0; gpt setenv boot2; mmc dev 0; mmc read 90000000 ${gpt_partition_addr} 4000; bootm 90000000; android
```

It keeps the stock MUTE (recovery) and VOL_DOWN (fastboot) keys, starts the VideoCore and its
framebuffer, loads `boot2` and boots it. If `bootm` fails (for example a bad checksum), it falls
through to the stock `android`. Never run `vc display fb pattern`: it ends the framebuffer and
the VC returns to its splash screen.

Set it from the u-boot prompt (stop autoboot by sending a key on the serial console):

```
setenv bootcmd '<MC74 Linux command above>'
setenv bootdelay 3
saveenv
```

Undo: `android` at the prompt boots stock once; `setenv bootcmd '<stock command>'; setenv bootdelay 1; saveenv` restores stock.
Back up `u-boot-env` and `u-boot-env2` (mmcblk0p10/p11) before the first `saveenv`.

## Tools (`tools/`)

All talk to the serial console (`/dev/ttyUSB*`, 115200 8N1, debug header) and, where noted, to
u-boot's USB fastboot.

| Tool | Does |
|---|---|
| `usbboot.py <uImage> <log> [--display] [--no-catch]` | RAM boot without flashing: catch the u-boot prompt, optionally bring up the display, `fastboot stage` + `fastboot continue` into `bootm 90000000` (bootcmd is set but never saved) |
| `flash_boot2.py <uImage> <log>` | Write a kernel into `boot2` from u-boot RAM (stage over fastboot, then a temporary bootcmd does `mmc write`) and boot it |
| `catch_uboot.py`, `ser.py`, `upload.py` | catch the prompt, send commands, upload a small text file |
| `push_file.py`, `pull_part.py` | copy a binary to the device / a partition or file from it, over serial (gzip + base64, md5 checked) |
| `ramboot.py` | slow fallback: YMODEM load over serial |
| `display-prep.txt` | the u-boot display bring-up commands |

If the fastboot USB device does not enumerate, replug the MC74's USB cable. The FT232 serial
adapter can lock up (LEDs stop); replug it, it may come back as another `/dev/ttyUSB*`.
