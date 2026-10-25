# Security model

Run setup scripts only after inspection. Linux bootstrap/build/activation needs
root because it installs packages, compiles system software and configures
services. Desktop preferences are applied as the selected non-root user.

* Loopback RDP plus an authenticated encrypted tunnel is the default. No public
  firewall port, auto-login, saved desktop password or anonymous access is added.
* Source downloads use HTTPS, fixed release URLs, SHA-256 checks, size limits and
  filtered tar extraction. Checksums are a reproducibility lock, not a substitute
  for reviewing upstream security releases.
* The native clipboard patch is version-specific and must be re-reviewed for
  future xrdp releases. Do not force it onto a different release with patch fuzz.
* Windows clipboard helpers process local clipboard data. Text-history support
  is opt-in and changes history eligibility for ordinary remote text. Do not use
  that option on shared machines or where remote text must never be retained.
* The optional per-user desktop-admin policy grants enumerated Flatpak operations
  without repeated authorization to one active sudo user. This includes repository
  modification, an intentional software-installation privilege. Other enumerated
  privileged actions retain temporary approval; unlisted actions use vendor
  policy. No wildcard Polkit rule, root GUI or passwordless arbitrary shell is added.
* Disabling idle lock is a separate opt-in. No suspend/manual lock policy or
  Windows sign-in policy is disabled.

Never commit provider keys, SSH private keys, `.aws`, browser profiles, backups,
chat databases, `.env` values, personal screenshots or credential-helper outputs.
Gitignore is a convenience, not proof that a file is safe to publish.

Report suspected vulnerabilities privately through the repository's GitHub
security reporting facility if available; otherwise contact the maintainer
without posting exploit data or secrets in a public issue. Do not assume public
issues are an appropriate place to disclose credentials.
