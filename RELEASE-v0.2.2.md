# SAGE v0.2.2 Release Notes

SAGE v0.2.2 is a patch release over v0.2.1. Protocol `sage/0.2`, wire version
`2`, the `0001_sage_0_2` migration baseline, and the 13 normative TCK vectors
are unchanged. No breaking changes.

## Fixes

- **Default SQLite path independent of the working directory (Issue #1).**
  The packaged `sage-api` service previously defaulted to
  `sqlite:///./sage.db`, which resolved relative to the process working
  directory and could fail or create an unexpected database when the service
  started from a non-writable or unexpected directory. The default is now the
  current user's home directory (`$HOME/sage.db`). An explicit
  `SAGE_DATABASE_URL` remains authoritative and is preserved exactly.
- **OpenClaw adapter type-check/build and conformance surface restored
  (Issue #3).** The adapter's npm type-check/build configuration and the
  conformance source used by the OpenClaw TCK runner are restored, so the
  packaged OpenClaw runtime ships with its independent conformance runner
  again.

## Documentation and configuration updates

- `docs/CONFIGURATION.md` documents the home-directory default for
  `SAGE_DATABASE_URL`.
- Install and release-asset references updated to the v0.2.2 artifact names.

## Release artifacts

| Asset | Name |
| --- | --- |
| Python wheel | `sage_agent_protocol-0.2.2-py3-none-any.whl` |
| Hermes plugin ZIP | `sage-hermes-plugin-v0.2.2.zip` |
| OpenClaw package | `sage-agent-openclaw-sage-0.2.2.tgz` |
| Source ZIP | `sage-plugin-v0.2.2.zip` |
| Verification report | `SAGE-v0.2.2-VERIFICATION.md` |
| Checksums | `SAGE-v0.2.2-SHA256SUMS.txt` |

## Checksums

SHA-256 checksums are computed by the release workflow and published with the
GitHub release in `SAGE-v0.2.2-SHA256SUMS.txt`. The table below is completed
at publish time:

| Asset | SHA-256 |
| --- | --- |
| `sage_agent_protocol-0.2.2-py3-none-any.whl` | _computed by release workflow_ |
| `sage-hermes-plugin-v0.2.2.zip` | _computed by release workflow_ |
| `sage-agent-openclaw-sage-0.2.2.tgz` | _computed by release workflow_ |
| `sage-plugin-v0.2.2.zip` | _computed by release workflow_ |

## Upgrade notes

- Install the new artifacts; the packaged wheel, Hermes plugin ZIP, and
  OpenClaw package are drop-in replacements for v0.2.1.
- `SAGE_DATABASE_URL`, when set, continues to take precedence over the default
  path. Verify your deployment's database URL after upgrading.
- Production still requires PostgreSQL (`SAGE_ENV=production` with a server
  database URL); SQLite remains rejected in production mode.
- Protocol, wire version, migration baseline, and TCK vectors are unchanged,
  so v0.2.1 peers and v0.2.2 peers interoperate.

## Rollback

- v0.2.1 remains available on the GitHub releases page with its original
  assets. To roll back, reinstall the v0.2.1 artifacts and restore your
  previous `SAGE_DATABASE_URL` configuration.
- Because the database schema, protocol, and wire version are unchanged
  between 0.2.1 and 0.2.2, no data migration is required to roll back.
