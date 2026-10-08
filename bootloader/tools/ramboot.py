#!/usr/bin/env python3
"""RAM-boot a uImage on the MC74 without touching flash.

Waits for the board to power up, stops u-boot autoboot on the serial console, loads the
uImage to 0xA2000000 with loady/YMODEM (lrzsz `sb`), checks it with iminfo, optionally
arms u-boot's watchdog, runs bootm and logs the console.

usage: ramboot.py <uImage> <logfile> [--watchdog] [--capture SECONDS]
"""
import os, subprocess, sys, time

import glob
TTY = (sorted(glob.glob('/dev/ttyUSB*')) or ['/dev/ttyUSB0'])[0]
img, logpath = sys.argv[1], sys.argv[2]
watchdog = '--watchdog' in sys.argv
capture = int(sys.argv[sys.argv.index('--capture') + 1]) if '--capture' in sys.argv else 180

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


def cmd(s, t=2, until=b'u-boot>'):
    os.write(fd, s.encode() + b'\r')
    return read_for(t, until)


def say(msg):
    print(msg, flush=True)
    log.write(('\n### ramboot: %s\n' % msg).encode())
    log.flush()


# 1. catch the prompt: send spaces until u-boot shows "u-boot>"
say('waiting for u-boot (power the board on now)')
buf = b''
while b'u-boot>' not in buf[-300:]:
    os.write(fd, b' ')
    buf += read_for(0.05)
say('caught u-boot prompt')
read_for(1)
os.write(fd, b'\x03\r')
read_for(1)

# 2. loady: send the command, then start sb right away so no 'C' handshake is lost
for attempt in range(3):
    os.write(fd, b'loady a2000000\r')
    read_for(0.3)
    say('sending %s via YMODEM (attempt %d)' % (img, attempt + 1))
    with open(TTY, 'rb', buffering=0) as rin, open(TTY, 'wb', buffering=0) as rout:
        r = subprocess.run(['sb', '-k', '--ymodem', img], stdin=rin, stdout=rout,
                           stderr=subprocess.PIPE)
    out = read_for(3, b'u-boot>')
    if r.returncode == 0:
        break
    say('sb failed: %s' % r.stderr.decode(errors='replace').replace('\r', '\n')[-200:])
    os.write(fd, b'\x03\r')
    read_for(3)
else:
    say('giving up after 3 attempts')
    sys.exit(1)

# 3. verify, then boot
info = cmd('iminfo a2000000', 4)
if b'Verifying Checksum ... OK' not in info:
    say('iminfo checksum failed, not booting')
    sys.exit(1)
if watchdog:
    cmd('set_watchdog on', 2)
say('bootm')
os.write(fd, b'bootm a2000000\r')
read_for(capture)
say('capture done')
