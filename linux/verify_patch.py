#!/usr/bin/env python3
"""Check patched source against the reviewed live implementation, before build."""
import argparse,hashlib,json,pathlib
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('source',type=pathlib.Path)
args=ap.parse_args()
lock=json.loads((pathlib.Path(__file__).resolve().parents[1]/'config/patched-source-sha256.json').read_text())
for name,digest in lock.items():
    # Git on Windows can normalize line endings. Native upstream source is LF.
    data=(args.source/name).read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(data).hexdigest()!=digest: raise SystemExit('Patched source mismatch: '+name)
print('All four patched source hashes match the reviewed implementation.')
