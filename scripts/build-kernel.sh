#!/bin/sh
# Build the MC74 kernel: patched bcm-kona-mainline + slim busybox initramfs + appended DTB,
# wrapped as a u-boot legacy uImage (load/entry 0xA0008000) for boot2 or a USB RAM boot.
# Needs: scripts/fetch-sources.sh first, arm-linux-gnueabihf-gcc, mkimage (u-boot-tools).
set -e
TOP=$(cd "$(dirname "$0")/.." && pwd)
SRC=$TOP/src
OUT=$TOP/out
CROSS=arm-linux-gnueabihf-
mkdir -p "$OUT"

# 1. kernel tree on a local branch with the patch series applied
cd "$SRC/linux"
if ! git rev-parse -q --verify mc74 >/dev/null; then
	git checkout -q -b mc74 546dcac3f6d7f8bcc10ddb0969a221cdf2b676b1
	git am -q "$TOP"/kernel/patches/*.patch
else
	git checkout -q mc74
fi

# 2. static busybox for the initramfs
cd "$SRC/busybox-1.38.0"
cp "$TOP/busybox/busybox-1.38.0.config" .config
make -s CROSS_COMPILE=$CROSS oldconfig </dev/null >/dev/null
make -s CROSS_COMPILE=$CROSS -j"$(nproc)"

# 3. initramfs list with absolute paths
sed -e "s|@DIR@|$TOP/kernel/initramfs|g" -e "s|@BUSYBOX@|$SRC/busybox-1.38.0/busybox|g" \
	"$TOP/kernel/initramfs/initramfs.list.in" > "$OUT/initramfs.list"

# 4. kernel
B=$OUT/build
mkdir -p "$B"
cp "$TOP/kernel/config/mc74_defconfig" "$SRC/linux/arch/arm/configs/mc74_defconfig"
cd "$SRC/linux"
make -s O="$B" ARCH=arm CROSS_COMPILE=$CROSS mc74_defconfig
./scripts/config --file "$B/.config" --set-str INITRAMFS_SOURCE "$OUT/initramfs.list"
make -s O="$B" ARCH=arm CROSS_COMPILE=$CROSS olddefconfig
make -s O="$B" ARCH=arm CROSS_COMPILE=$CROSS -j"$(nproc)" zImage dtbs

# 5. zImage + appended DTB -> uImage (CONFIG_ARM_APPENDED_DTB)
cat "$B/arch/arm/boot/zImage" "$B/arch/arm/boot/dts/broadcom/bcm28155-cisco-mc74.dtb" > "$OUT/zImage-dtb"
mkimage -A arm -O linux -T kernel -C none -a 0xA0008000 -e 0xA0008000 \
	-n "MC74 Linux $(git -C "$SRC/linux" describe --always)" -d "$OUT/zImage-dtb" "$OUT/uImage-mc74"
size=$(stat -c %s "$OUT/uImage-mc74")
echo "built $OUT/uImage-mc74 ($size bytes, boot2 holds 8388608)"
[ "$size" -le 8388608 ] || { echo "too large for boot2"; exit 1; }
