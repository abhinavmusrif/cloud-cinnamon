#!/usr/bin/env python3
"""Private, allowlisted desktop-settings backup. Never includes credentials."""
import argparse,datetime,json,pathlib,subprocess,tarfile
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('destination',type=pathlib.Path,help='Outside this repository, on your private backup storage')
args=ap.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
dest=args.destination.expanduser().resolve()
if dest.is_relative_to(root): raise SystemExit('Backups must stay outside the public repository')
dest.mkdir(parents=True,exist_ok=True,mode=0o700)
path=dest/('desktop-profile-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.tar.gz')
home=pathlib.Path.home()
with tarfile.open(path,'w:gz') as archive:
    for rel in ['.xsession','.config/cinnamon/spices','.config/nemo/desktop-metadata','.local/state/cloud-cinnamon']:
        p=home/rel
        if not p.exists() or p.is_symlink(): continue
        entries=[p]+(list(p.rglob('*')) if p.is_dir() else [])
        for entry in entries:
            if entry.is_file() and not entry.is_symlink() and entry.stat().st_size<8*1024*1024:
                archive.add(entry,arcname=str(entry.relative_to(home)),recursive=False)
path.chmod(0o600)
print('Private settings archive:',path)
print('Does not back up documents, browser profiles, credentials, or application databases.')
