#!/usr/bin/env bash
# Build and test first. Activation is a separate, explicit operation.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
. /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 24.04 ]] || { echo 'Ubuntu 24.04 required.' >&2; exit 1; }
HERE=$(cd -- "$(dirname -- "$0")/.." && pwd)
ROOT=/var/lib/cloud-cinnamon
PREFIX=/opt/cloud-cinnamon/rdp-0.10.6.1
MODE=${1:-}
[[ -z $MODE || $MODE == --validate-only ]] || { echo 'Use --validate-only or no arguments.' >&2; exit 1; }
JOBS=${JOBS:-2}
[[ $JOBS =~ ^[1-8]$ ]] || { echo 'JOBS must be 1..8' >&2; exit 1; }
[[ $MODE == --validate-only || ! -e $PREFIX ]] || { echo 'Build prefix exists; use its rollback or inspect it first.' >&2; exit 1; }
mkdir -p "$ROOT"
exec 9>"$ROOT/build.lock"
flock -n 9 || { echo 'Another build is running.' >&2; exit 1; }
WORK=$(mktemp -d "$ROOT/build-XXXXXXXX")
if [[ $MODE == --validate-only ]]; then PREFIX="$WORK/prefix"; fi
echo "Build log: $WORK/build.log"
exec > >(tee -a "$WORK/build.log") 2>&1
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
if [[ $MODE != --validate-only ]]; then
 apt-get update
 apt-get install -y --no-remove build-essential autoconf automake libtool pkg-config \
  nasm check libcmocka-dev libpam0g-dev libssl-dev libx11-dev libxrandr-dev \
  libxfixes-dev libfuse3-dev libjpeg-dev libpixman-1-dev libx264-dev \
  libfreetype-dev libimlib2-dev xserver-xorg-dev libxfont-dev libxkbfile-dev \
  autoconf-archive libpng-dev python3-pil patch
fi
python3 "$HERE/linux/fetch_sources.py" "$WORK"
cd "$WORK/xrdp-0.10.6.1"
patch --batch --fuzz=0 -p1 < "$HERE/patches/xrdp-0.10.6.1-clipboard.patch"
python3 "$HERE/linux/verify_patch.py" "$PWD"
./bootstrap
./configure --prefix="$PREFIX" --enable-strict-locations --sysconfdir="$PREFIX/etc" \
  --localstatedir="$PREFIX/var" --with-socketdir=/run/cloud-cinnamon-rdp \
  --with-pamconfdir="$PREFIX/etc/pam.d" --with-systemdsystemunitdir=no \
  --enable-ipv6 --enable-fuse --enable-jpeg --enable-pixman --enable-x264 \
  --enable-tests --with-imlib2 --with-freetype2
make -j"$JOBS"
make check
# Install through libtool. Copying sesman/chansrv/xrdp-chansrv directly copies
# a shell wrapper, not the ELF executable. DESTDIR is mandatory here.
make install DESTDIR="$WORK/stage"
cd "$WORK/xorgxrdp-0.10.5"
./bootstrap
XRDP_CFLAGS="-I$WORK/stage$PREFIX/include" ./configure \
  --prefix="$PREFIX" --enable-strict-locations --sysconfdir="$PREFIX/etc" --libdir="$PREFIX/lib"
make -j"$JOBS"
make check
make install DESTDIR="$WORK/stage"
python3 "$HERE/tests/test_clipboard_codec.py" --header "$WORK/xrdp-0.10.6.1/sesman/chansrv/clipboard_png.h"
python3 - "$WORK/stage$PREFIX" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1])
for n in ('sbin/xrdp','sbin/xrdp-sesman','sbin/xrdp-chansrv'):
    if (p/n).read_bytes()[:4]!=b'\x7fELF': raise SystemExit('Not an installed ELF: '+n)
PY
if [[ $MODE == --validate-only ]]; then
  echo "VALIDATE_SUCCESS: compiled, native-tested and staged at $WORK/stage. No installation or live service changes."
  exit 0
fi
mkdir -p "$PREFIX"
cp -a "$WORK/stage$PREFIX/." "$PREFIX/"
for binary in xrdp xrdp-sesman xrdp-chansrv; do
  if ldd "$PREFIX/sbin/$binary" | grep -q 'not found'; then echo 'Unresolved native dependency' >&2; exit 1; fi
done
cp "$HERE/config/sources.json" "$PREFIX/source-lock.json"
sha256sum "$PREFIX"/sbin/xrdp* > "$PREFIX/artifact-sha256.txt"
touch "$PREFIX/build-tested"
echo 'Built and tested. No live service or session changed.'
echo 'Activate after saving desktop work: sudo bash linux/activate-rdp.sh --activate'
