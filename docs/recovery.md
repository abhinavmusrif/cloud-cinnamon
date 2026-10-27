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

## Orphaned desktops and hidden applications

A display number such as `:10` or `:11` identifies an Xorg desktop, not a second
server. `loginctl list-sessions` and `loginctl show-session SESSION -p Display -p State`
can reveal an old closing desktop and a newer active one under the same account.
If an old session's `xrdp-sesexec` manager has gone away while Xorg and GUI apps
remain, reconnecting cannot simply select that old desktop. Single-instance
application locks can keep sending new launches to those old windows.

1. Preserve current work. Keep SSH/provider-console access available. Do not
   restart RDP to diagnose a live desktop.
2. Compare `systemctl show xrdp-sesman -p ExecMainStartTimestamp` with the old
   session's start and `/var/log/apt/history.log`. Ubuntu 24.04 shared-library
   updates can trigger automatic `needrestart` service restarts. An update and
   daemon restart at matching times support this diagnosis; inspect privileged
   logs to confirm it when available.
3. Apply `sudo python3 linux/session_safety.py --apply`. Check it with
   `python3 linux/session_safety.py --check`. This is safe while connected and
   adds no restart, logout, network or authentication changes.
4. For configuration-only changes, prefer `sudo systemctl reload xrdp-sesman`
   after reviewing the settings. A binary/library upgrade still needs a planned
   logged-out restart; a configuration reload does not activate new binaries.
5. Recover an affected GUI app individually: identify its actual process and
   X11 connection, close it gracefully, and relaunch it in the current desktop
   using the same application profile. Browser session restoration can recover
   saved tabs, but unsaved form/editor state is not guaranteed. Never blindly
   kill every user process or remove singleton locks from a live profile.
6. Retire the old orphan only after its applications/jobs have been reviewed
   and work saved. Existing orphans are not automatically terminated by this kit.

The safeguard backs up earlier versions of its two managed files under
`/var/lib/cloud-cinnamon/session-safety/` with a manifest identifying previously
absent files. To undo it, restore earlier file contents from the chosen backup
(or remove only files the manifest marks previously absent), then run
`sudo systemctl daemon-reload`. Do not remove other needrestart/systemd policies.
This changes future restart selection; existing RDP processes need no restart.

Upstream references:
[Ubuntu service restarts](https://ubuntu.com/server/docs/how-to/software/automatic-updates/#service-restarts),
[xrdp session management](https://github.com/neutrinolabs/xrdp/wiki/SessionManagementArchitecture),
[xrdp 0.10.6.1 reload unit](https://github.com/neutrinolabs/xrdp/blob/v0.10.6.1/instfiles/xrdp-sesman.service.in).
