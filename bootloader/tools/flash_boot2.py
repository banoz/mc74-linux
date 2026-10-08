#!/usr/bin/env python3
"""Write a uImage into boot2 from u-boot RAM, then boot it (owner-approved 2026-10-07).
The device must sit at the u-boot prompt. Stages the image over fastboot into 0x90000000, and a
temporary (unsaved) bootcmd writes it to boot2 with `mmc write` and then bootm's it.
usage: flash_boot2.py <uImage> <logfile>"""
import os, subprocess, sys, time, glob
img, logpath = sys.argv[1], sys.argv[2]
blocks = (os.path.getsize(img) + 511) // 512
assert blocks <= 0x4000, 'image larger than boot2 (8 MB)'
fd = os.open(sorted(glob.glob('/dev/ttyUSB*'))[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
log = open(logpath, 'ab')
def rd(t, until=None):
    buf = b''; end = time.time() + t
    while time.time() < end:
        try:
            b = os.read(fd, 4096); buf += b; log.write(b); log.flush()
            if until and until in buf: break
        except BlockingIOError: time.sleep(0.02)
    return buf
def cmd(c, t=3): os.write(fd, c.encode() + b'\r'); return rd(t, b'u-boot>')
cmd('gpio set 95; gpio set 6; gpio set 96; i2c mw 17 0 fc; mipi init')
cmd('vc run', 8); rd(10)
cmd('vc display power on')
for i in range(5):
    if b'fb init 800x1280' in cmd('vc display fb init', 8): break
    rd(3)
cmd('vc display fb update 0')
cmd("setenv bootcmd 'gpt setenv boot2; mmc dev 0; mmc write 90000000 ${gpt_partition_addr} %x; bootm 90000000'" % blocks)
os.write(fd, b'fastboot\r')
for _ in range(60):
    rd(1)
    if subprocess.run(['fastboot', 'devices'], capture_output=True, text=True).stdout.strip(): break
else: sys.exit('fastboot device never appeared')
print(subprocess.run(['fastboot', 'stage', img], capture_output=True, text=True).stderr.strip()[-120:])
print(subprocess.run(['fastboot', 'continue'], capture_output=True, text=True).stderr.strip()[-80:])
out = rd(20)
print([l for l in out.decode('latin1').splitlines() if 'MMC write' in l or 'blocks written' in l])
rd(70)
