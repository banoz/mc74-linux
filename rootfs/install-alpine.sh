#!/bin/sh
# Install Alpine Linux armv7 onto system2 (mmcblk0p18). Run from the RAM-booted busybox shell.
# Owner approved formatting system2 on 2026-10-07.
set -e
DEV=/dev/mmcblk0p18
TAR=/tmp/alpine-minirootfs-3.24.2-armv7.tar.gz
grep -q PARTNAME=system2 /sys/class/block/mmcblk0p18/uevent || { echo "p18 is not system2, abort"; exit 1; }
grep -q "^$DEV " /proc/mounts && { echo "$DEV is mounted, abort"; exit 1; }
mkdir -p /tmp/alp; tar xzf $TAR -C /tmp/alp; cp /etc/resolv.conf /tmp/alp/etc/
mount -t proc proc /tmp/alp/proc; mount -o bind /sys /tmp/alp/sys; mount -o bind /dev /tmp/alp/dev
chroot /tmp/alp /sbin/apk add -q --no-progress e2fsprogs
chroot /tmp/alp /sbin/mkfs.ext4 -q -F -L mc74root $DEV
umount /tmp/alp/dev /tmp/alp/sys /tmp/alp/proc
mkdir -p /mnt/root; mount -t ext4 $DEV /mnt/root
tar xzf $TAR -C /mnt/root; cp /etc/resolv.conf /mnt/root/etc/
mount -t proc proc /mnt/root/proc; mount -o bind /sys /mnt/root/sys; mount -o bind /dev /mnt/root/dev
chroot /mnt/root /sbin/apk add -q --no-progress alpine-base openrc busybox-openrc busybox-mdev-openrc e2fsprogs alsa-utils iw wpa_supplicant dropbear dropbear-openrc chrony ca-certificates tzdata python3 py3-pip
echo INSTALL-DONE
df -h /mnt/root
