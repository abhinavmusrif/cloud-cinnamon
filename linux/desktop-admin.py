#!/usr/bin/env python3
"""Explicitly opt one existing sudo user into narrower remote desktop policies."""
import argparse
import json
import os
import pathlib
import pwd
import re
import grp

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--user',required=True)
ap.add_argument('--enable',action='store_true')
ap.add_argument('--remove',action='store_true')
args=ap.parse_args()
if os.geteuid()!=0 or args.enable==args.remove: raise SystemExit('Use sudo and exactly one of --enable / --remove')
if not re.fullmatch(r'[a-z_][a-z0-9_-]*',args.user): raise SystemExit('Invalid user')
user=pwd.getpwnam(args.user)
if user.pw_uid==0 or grp.getgrnam('sudo').gr_gid not in os.getgrouplist(user.pw_name,user.pw_gid): raise SystemExit('An existing non-root sudo user is required')
p=pathlib.Path('/etc/polkit-1/rules.d/48-cloud-cinnamon-'+args.user+'.rules')
if args.remove:
    p.unlink(missing_ok=True)
    print('Removed this kit\'s user-specific policy; vendor policy remains.')
else:
    # Installing software without repeated prompts is an explicit privilege
    # choice. No arbitrary action wildcard or sudo policy is introduced.
    ordinary=['app-install','runtime-install','app-update','runtime-update','app-uninstall','runtime-uninstall','modify-repo','update-remote','appstream-update','metadata-update']
    retain=['org.freedesktop.Flatpak.'+x for x in ['configure-remote','configure','install-bundle']]
    retain+=['org.freedesktop.packagekit.'+x for x in ['package-install','package-reinstall','system-update','package-eula-accept']]
    retain+=['com.ubuntu.whoopsiepreferences.change']
    text='''// Explicit per-user remote desktop administration profile.
polkit.addRule(function(action, subject) {
  if (subject.user !== USER || !subject.active || !subject.isInGroup("sudo")) return polkit.Result.NOT_HANDLED;
  if (ORDINARY.indexOf(action.id) !== -1) return polkit.Result.YES;
  if (RETAIN.indexOf(action.id) !== -1) return polkit.Result.AUTH_ADMIN_KEEP;
  return polkit.Result.NOT_HANDLED;
});
'''.replace('USER',json.dumps(args.user)).replace('ORDINARY',json.dumps(['org.freedesktop.Flatpak.'+x for x in ordinary])).replace('RETAIN',json.dumps(retain))
    if p.exists() and p.read_text()!=text: raise SystemExit('Existing policy differs; review it before replacing')
    p.write_text(text);p.chmod(0o644)
    print('Enabled only for',args.user,'in an active sudo-user session.')
