#!/bin/sh
# Fix the Alpine serial console + chrony/hwclock on system2 (from the initramfs shell).
set -e
R=/mnt/root
mkdir -p $R; mount -t ext4 /dev/mmcblk0p18 $R
sed -i '/ttyS0/d' $R/etc/inittab
echo 'ttyS0::respawn:/sbin/getty -n -l /bin/sh -L 115200 ttyS0 vt100' >> $R/etc/inittab
sed -i 's/^#*ARGS=.*/ARGS="-F 0"/' $R/etc/conf.d/chronyd
grep -q '^ARGS=' $R/etc/conf.d/chronyd || echo 'ARGS="-F 0"' >> $R/etc/conf.d/chronyd
rm -f $R/etc/runlevels/*/hwclock; ln -sf /etc/init.d/swclock $R/etc/runlevels/boot/swclock
grep ttyS0 $R/etc/inittab; grep ARGS $R/etc/conf.d/chronyd
umount $R; sync; echo FIX-DONE
