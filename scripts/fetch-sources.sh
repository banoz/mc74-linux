#!/bin/sh
# Fetch the pinned upstream sources (see sources.lock) into ./src and verify them.
set -e
cd "$(dirname "$0")/.."
mkdir -p src && cd src

fetch() {	# fetch <url> <sha256>
	f=$(basename "$1")
	[ -f "$f" ] || curl -fL -o "$f" "$1"
	echo "$2  $f" | sha256sum -c -
}

if [ ! -d linux ]; then
	git clone --branch kona/7.1 https://github.com/bcm-kona-mainline/linux.git linux
fi
git -C linux checkout -q 546dcac3f6d7f8bcc10ddb0969a221cdf2b676b1
echo "linux: $(git -C linux rev-parse HEAD)"

fetch https://busybox.net/downloads/busybox-1.38.0.tar.bz2 \
	34f9ea6ff8636f2c9241153b9114eefa9e65674a45318ae1ef95bb5f31c53bb2
[ -d busybox-1.38.0 ] || tar xjf busybox-1.38.0.tar.bz2
