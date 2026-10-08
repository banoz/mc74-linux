#!/usr/bin/env python3
"""Stop MC74 u-boot autoboot: send spaces until the u-boot> prompt appears (timeout arg, default 120 s)."""
import os, sys, time
fd = os.open((sorted(__import__('glob').glob('/dev/ttyUSB*')) or ['/dev/ttyUSB0'])[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
buf = b''; end = time.time() + (float(sys.argv[1]) if len(sys.argv) > 1 else 120)
while time.time() < end and b'u-boot>' not in buf[-300:]:
    os.write(fd, b' ')
    try: buf += os.read(fd, 4096)
    except BlockingIOError: pass
    time.sleep(0.05)
print('caught' if b'u-boot>' in buf[-300:] else 'timeout')
sys.exit(0 if b'u-boot>' in buf[-300:] else 1)
