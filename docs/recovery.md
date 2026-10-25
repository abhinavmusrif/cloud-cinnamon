# Recovery and rollback

## What to keep

Keep three independent things:

1. **This source repository:** pinned versions, patch, scripts and documentation.
2. **Private user data:** documents, projects, application databases and anything
   you cannot recreate. Back these up encrypted using your own storage policy.
3. **Private identity/recovery information:** provider access, SSH keys and app
   login recovery. Keep these in your credential manager, never in this repo.

The public repository deliberately contains none of the original machine's
account IDs, hostnames, browser profiles, credentials, chat history or home data.
An OS snapshot is useful as an additional backup but is provider-dependent.

## Save desktop preferences

As the desktop user:

```bash
python3 linux/backup-profile.py /path/to/private-backup-storage
```

This allowlists Cinnamon applet settings, Nemo desktop metadata, `.xsession` and
this kit's setting snapshots. It excludes browser profiles, application databases
and credentials. Applet configurations can still contain private preferences;
treat the archive as private. It does not back up documents. Verify a separate
document backup before deleting any machine or account.

## Restore to a different provider

1. Create an Ubuntu 24.04 x64 server. Keep console/SSH recovery available.
2. Prepare a non-root desktop account, password and your own administrative access.
3. Block public 3389 in the provider firewall; clone the repository at the desired
   tag/commit and run the README setup/build/activation commands.
4. Establish SSH, VPN or provider-private access; connect via loopback forwarding.
5. Apply the profile to the new user's actual session. Restore selected private
   settings only after reviewing paths and applet compatibility. Do not blindly
   extract old archives over a different user's home.
6. Restore documents and applications; sign in with your own accounts. Reinstall
   optional Chrome/editor tools from their official channels rather than copying
   an entire Windows application installation into Linux.
7. Run `bash linux/doctor.sh` and the clipboard regression checklist. Keep the
   previous machine until new data and access are verified.

## Undo desktop appearance changes

Use the path printed when the profile was applied:

```bash
python3 linux/desktop.py --user YOUR_USER --restore /home/YOUR_USER/.local/state/cloud-cinnamon/SNAPSHOT.json
```

Snapshots are local to the original user, not a cross-account restore format.
The root wrapper drops to that user before changing settings. No automatic shell
restart is attempted. Optional administrator policy can be removed with:

```bash
sudo python3 linux/desktop-admin.py --user YOUR_USER --remove
```

## Roll back RDP

Log out of Cinnamon first, keeping SSH/console open:

```bash
sudo bash linux/rollback-rdp.sh
```

The kit restores the prior drop-in and keeps distro binaries/configuration and
source logs. It does not remove packages or delete your home. If the activation
itself fails, the error handler attempts this same rollback. Rollback can fail
too if the prior service was broken; retain provider-console access.

The first base install backs up `/etc/xrdp/xrdp.ini` beside itself and replaces
only its listener with loopback. It also backs up an existing `.xsession`.
It refuses base provisioning while Cinnamon is running, and temporarily masks
a stopped/new xrdp service during installation to prevent early public exposure.
Those are separate base-install changes; review/restore their saved copies if
uninstalling the entire desktop. Package removal is intentionally not automatic.

## Removing an obsolete cloud user

There is no automatic `userdel ubuntu` in this kit. Cloud images use different
default users and provider agents may depend on them. Before optional cleanup:

* Verify the replacement user's login, sudo, recovery and desktop access.
* Check active sessions/processes, cron, systemd services, SSH access, home data,
  mounts, files outside the home and sudoers entries owned by the old UID/GID.
* Make a root-only home archive without following symlinks. Verify archive
  contents/hashes. Record reviewed ownership paths and permissions.
* Reassign only reviewed files, remove only obsolete user-specific sudo rules,
  validate with `visudo -c`, then delete the inactive account.
* Check for orphaned UID/GID files and retest the replacement user and services.

Deleting a user is not required to recover this desktop. Never make it a silent
side effect of installation.
