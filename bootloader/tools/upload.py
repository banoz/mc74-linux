#!/usr/bin/env python3
"""Upload a small text file to the MC74 shell over serial: upload.py <local> <remote>"""
import os, sys, time
local, remote = sys.argv[1], sys.argv[2]
fd = os.open((sorted(__import__('glob').glob('/dev/ttyUSB*')) or ['/dev/ttyUSB0'])[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
os.write(fd, ("cat > %s <<'__EOF__'\r" % remote).encode()); time.sleep(0.2)
for line in open(local).read().splitlines():
    os.write(fd, (line + '\r').encode()); time.sleep(0.06)
os.write(fd, b'__EOF__\r'); time.sleep(0.5)
