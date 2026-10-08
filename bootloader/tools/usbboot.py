#!/usr/bin/env python3
"""RAM-boot a uImage on the MC74 over USB fastboot, without touching flash.

Catches the u-boot prompt on serial, sets a RAM-only bootcmd (never saveenv),
enters fastboot, stages the uImage into u-boot's download buffer (0x90000000)
and sends `fastboot continue`, which makes u-boot run bootcmd = bootm 90000000.
Logs the serial console throughout.

usage: usbboot.py <uImage> <logfile> [--capture SECONDS] [--no-catch] [--display]
"""
import os, subprocess, sys, time

import glob
TTY = (sorted(glob.glob('/dev/ttyUSB*')) or ['/dev/ttyUSB0'])[0]
img, logpath = sys.argv[1], sys.argv[2]
capture = int(sys.argv[sys.argv.index('--capture') + 1]) if '--capture' in sys.argv else 240
catch = '--no-catch' not in sys.argv
display = '--display' in sys.argv

subprocess.run(['stty', '-F', TTY, '115200', 'raw', '-echo', 'cs8', '-cstopb', '-parenb',
                '-crtscts', '-ixon', '-ixoff', 'clocal'], check=True)
fd = os.open(TTY, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
log = open(logpath, 'ab')


def read_for(t, until=None):
    buf = b''
    end = time.time() + t
    while time.time() < end:
        try:
            b = os.read(fd, 4096)
            buf += b
            log.write(b)
            log.flush()
            if until and until in buf:
                return buf
        except BlockingIOError:
            time.sleep(0.02)
    return buf


def say(msg):
    print(msg, flush=True)
    log.write(('\n### usbboot: %s\n' % msg).encode())
    log.flush()


if catch:
    say('waiting for u-boot (power the board on now)')
    buf = b''
    while b'u-boot>' not in buf[-300:]:
        os.write(fd, b' ')
        buf += read_for(0.05)
    say('caught u-boot prompt')
    read_for(1)

os.write(fd, b'\x03\r')
read_for(1)
if display:
    # stock display prep + VideoCore framebuffer (never run `vc display fb pattern`)
    for c, t in ((b'gpio set 95; gpio set 6; gpio set 96; i2c mw 17 0 fc; mipi init', 3),
                 (b'vc run', 8)):
        os.write(fd, c + b'\r')
        out = read_for(t, b'u-boot>')
    read_for(10)   # the VC firmware needs a few seconds before it answers display IPC
    os.write(fd, b'vc display power on\r')
    read_for(3, b'u-boot>')
    for attempt in range(5):
        os.write(fd, b'vc display fb init\r')
        out = read_for(8, b'u-boot>')
        if b'fb init 800x1280' in out:
            break
        say('fb init not ready (attempt %d), retrying' % (attempt + 1))
        read_for(3)
    else:
        say('VC framebuffer init failed')
        sys.exit(1)
    os.write(fd, b'vc display fb update 0\r')
    out = read_for(3, b'u-boot>')
    say('display prep done: ' + out.decode('latin1', 'replace').strip().replace('\r', ' ')[-120:])
os.write(fd, b'setenv bootcmd bootm 90000000\r')
read_for(1, b'u-boot>')
os.write(fd, b'fastboot\r')
say('entered fastboot, waiting for USB')

for _ in range(60):
    read_for(1)
    if subprocess.run(['fastboot', 'devices'], capture_output=True, text=True).stdout.strip():
        break
else:
    say('fastboot device never appeared on USB')
    sys.exit(1)

say('staging %s' % img)
r = subprocess.run(['fastboot', 'stage', img], capture_output=True, text=True)
say('stage: rc=%d %s' % (r.returncode, (r.stdout + r.stderr).strip()[-200:]))
if r.returncode:
    sys.exit(1)
r = subprocess.run(['fastboot', 'continue'], capture_output=True, text=True)
say('continue: rc=%d %s' % (r.returncode, (r.stdout + r.stderr).strip()[-200:]))
read_for(capture)
say('capture done')
