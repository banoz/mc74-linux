#!/usr/bin/env python3
"""Send commands to the MC74 serial console and print the replies.
usage: ser.py <wait_seconds> <cmd> [<cmd> ...]   (escapes like \\r, \\x03 are interpreted)"""
import os, sys, time
fd = os.open((sorted(__import__('glob').glob('/dev/ttyUSB*')) or ['/dev/ttyUSB0'])[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
def rd(t):
    out = b''; end = time.time() + t
    while time.time() < end:
        try:
            b = os.read(fd, 4096)
            if b: out += b; end = max(end, time.time() + 0.6)
        except BlockingIOError: time.sleep(0.05)
    return out
for cmd in sys.argv[2:]:
    os.write(fd, cmd.encode().decode('unicode_escape').encode('latin1'))
    sys.stdout.write(rd(float(sys.argv[1])).decode('latin1').replace('\r', ''))
