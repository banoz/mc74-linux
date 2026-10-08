#!/usr/bin/env python3
"""Copy a (small) eMMC partition from the MC74 shell to the PC over serial (gzip+base64).
usage: pull_part.py <partition-device> <local-file>"""
import os, time, glob, re, base64, gzip, sys
dev, out = sys.argv[1], sys.argv[2]
fd = os.open(sorted(glob.glob('/dev/ttyUSB*'))[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
os.write(fd, ('dd if=%s bs=4096 2>/dev/null | gzip -9 | base64 -w 0; echo; echo @@EN""D@@\r' % dev).encode())
buf = b''; end = time.time() + 600
while time.time() < end and b'@@END@@' not in buf:
    try:
        buf += os.read(fd, 65536)
    except BlockingIOError:
        time.sleep(0.02)
m = max(re.findall(r'[A-Za-z0-9+/=]{100,}', buf.decode('latin1')), key=len)
open(out, 'wb').write(gzip.decompress(base64.b64decode(m)))
print(out, os.path.getsize(out))
