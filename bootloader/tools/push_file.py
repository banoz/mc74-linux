#!/usr/bin/env python3
"""Copy a binary file to the MC74 shell over serial (gzip + base64 heredoc), verify md5.
usage: push_file.py <local> <remote>"""
import os, sys, time, glob, gzip, base64, hashlib, textwrap
local, remote = sys.argv[1], sys.argv[2]
data = open(local, 'rb').read()
b64 = base64.b64encode(gzip.compress(data, 9)).decode()
fd = os.open(sorted(glob.glob('/dev/ttyUSB*'))[0], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
def drain():
    try:
        while os.read(fd, 65536): pass
    except BlockingIOError: pass
os.write(fd, b"stty -echo; cat > /tmp/push.b64 <<'__EOF__'\r"); time.sleep(0.3)
for i, line in enumerate(textwrap.wrap(b64, 76)):
    os.write(fd, (line + '\r').encode()); time.sleep(0.009)
    if i % 50 == 0: drain()
os.write(fd, b'__EOF__\r'); time.sleep(1)
os.write(fd, ('base64 -d /tmp/push.b64 | gunzip > %s; rm /tmp/push.b64; stty echo; md5sum %s\r' % (remote, remote)).encode())
time.sleep(4); out = b''
try:
    while True: out += os.read(fd, 65536)
except BlockingIOError: pass
want = hashlib.md5(data).hexdigest()
print('ok' if want.encode() in out else 'MD5 MISMATCH', want, len(b64), 'b64 bytes')
