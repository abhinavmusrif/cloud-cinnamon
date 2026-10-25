# Private access, across providers

The desktop configuration does not depend on AWS. Start with Ubuntu 24.04 x64,
systemd and an existing administrator account. Disk encryption, snapshots,
firewall policy, billing and provider recovery access remain provider concerns.

## SSH (general cloud providers)

Verify ordinary key-based SSH login first. The Windows launcher uses BatchMode
and fails instead of hanging on a hidden password or host-key prompt. It opens
only a local listener and closes the tunnel it started when its RDP process exits.
Errors are in `%LOCALAPPDATA%\CloudCinnamon\tunnel-error.log`.

For a manually managed tunnel:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:50001:127.0.0.1:3389 your-user@your-host
```

Run `windows/Connect-Desktop.ps1 -Transport ExistingTunnel` in another terminal.
ExistingTunnel explicitly trusts the listener you prepared; verify that process
and destination yourself. No SSH host, IP or key is built into the repository.

## AWS SSM (optional)

Install AWS CLI v2 and the Session Manager plugin on Windows. The instance must
be managed by SSM, have the appropriate instance role and outbound connectivity.
Sign in to a least-privilege AWS CLI profile using your own approved mechanism.
Do not create permanent account-admin keys for a desktop tunnel.

```powershell
.\windows\Connect-Desktop.ps1 -Transport SSM -AwsProfile YOUR_PROFILE `
  -Region YOUR_REGION -InstanceId YOUR_INSTANCE
```

The launcher calls `AWS-StartPortForwardingSession` for remote port 3389.
It does not install IAM roles, register access keys, copy Windows credentials,
change cloud security groups or launch more instances. No inbound RDP security
group rule is needed for this transport.

Provider prerequisites:
[AWS Session Manager requirements](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html),
[port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html).

## RDP TLS and login

The server uses TLS and the packaged xrdp certificate/key. On a fresh server,
check their fingerprint from your authenticated administration session:

```bash
sudo openssl x509 -in /etc/xrdp/cert.pem -noout -sha256 -fingerprint -subject
```

The Windows template retains certificate warnings (`authentication level=2`).
Review rather than suppress them. For managed deployments install a certificate
appropriate for your RDP hostname and configure the corresponding client name.
The encrypted tunnel does not replace the desktop user's Linux authentication.

## Windows helper lifecycle

The image helper is started hidden for the RDP session, with a per-user mutex.
It exits after no mstsc process has existed for 30 seconds. It may remain active
if you keep another RDP connection open. It reads the current local clipboard
to add PNG and, only with opt-in, process remote text; it has no network access.
There is no persistent startup task, watchdog, password storage or automatic
Windows reboot policy in this kit. Reconnect by running the launcher again.
