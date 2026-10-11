# Signing happens at the share, not in CI

The toolkit is distributed through `X:\Apps\image-toolkit.exe` — the updater
checks that path by default, and staff run from there. The GitHub release asset
is a build output that happens to be downloadable, not the distribution
channel.

Signing is done with the enterprise key when the EXE is placed on the share.
The release workflow does not sign, and deliberately holds no certificate: an
enterprise key that signs more than this one application should not live in a
GitHub secret (2026-09-18).

## Considered options

Signing in CI was the obvious alternative and is the reason this is written
down. It needs the certificate and its password in GitHub Actions secrets,
which widens the blast radius of that key far beyond this project. A
self-hosted Windows runner would give the same automation without the
exposure, and remains the option to revisit if the manual step starts being
missed.

## Consequences

- Anyone who downloads from GitHub Releases instead of the share gets an
  unsigned binary, with the SmartScreen warnings that implies. The release body
  should say the supported download is the share.
- The signing step is manual, so it can be forgotten. If that happens more than
  once, the fix is a CI check that fails the release when the asset is
  unsigned — not moving the key into CI.
- Signing alone does not clear SmartScreen. Reputation is a separate mechanism,
  tracked as `P2-W2-E1-024`.
