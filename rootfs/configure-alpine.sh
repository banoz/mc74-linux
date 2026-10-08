#!/bin/sh
# Configure the Alpine root on system2 (mounted at /mnt/root) for the MC74.
set -e
R=/mnt/root
echo mc74 > $R/etc/hostname
cat > $R/etc/fstab <<'F'
/dev/mmcblk0p18	/	ext4	rw,noatime	0 1
tmpfs	/tmp	tmpfs	nosuid,nodev	0 0
F
cat > $R/etc/network/interfaces <<'F'
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
F
# serial console: root shell without login (bench device)
sed -i 's|^tty1::|#tty1::|; s|^tty2::|#tty2::|; s|^tty3::|#tty3::|; s|^tty4::|#tty4::|; s|^tty5::|#tty5::|; s|^tty6::|#tty6::|' $R/etc/inittab
grep -q ttyS0 $R/etc/inittab || echo 'ttyS0::respawn:/sbin/getty -n -l /bin/sh -L 115200 ttyS0 vt100' >> $R/etc/inittab
echo ttyS0 >> $R/etc/securetty
mkdir -p $R/lib/firmware/brcm && cp -a /lib/firmware/brcm/. $R/lib/firmware/brcm/
cp /etc/asound.conf $R/etc/ 2>/dev/null || true
chroot $R /bin/sh -c '
for s in devfs dmesg mdev hwdrivers; do rc-update add $s sysinit; done
for s in modules sysctl hostname bootmisc syslog networking chronyd dropbear; do rc-update add $s boot 2>/dev/null || rc-update add $s default; done
for s in mount-ro killprocs savecache; do rc-update add $s shutdown; done
setup-timezone -z UTC >/dev/null 2>&1 || true
'
echo CONFIG-DONE
