# Changelog

## 0.2.2

- Patch release over 0.2.1. Protocol `sage/0.2`, wire version `2`, migration baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.
- Fixes the packaged `sage-api` default SQLite path so it no longer depends on the process working directory (Issue #1): the default database is `$HOME/sage.db`, and an explicit `SAGE_DATABASE_URL` always takes precedence. Production still requires PostgreSQL.
- Restores the OpenClaw adapter type-check/build surface and the missing conformance source used by the OpenClaw TCK runner (Issue #3).
- Updates documentation, release artifacts, and verification status for v0.2.2.

## 0.2.1

- Keeps protocol `sage/0.2`, wire version `2`, and migration baseline `0001_sage_0_2` unchanged.
- Constrains Hermes `sage_handoff.content` to raw structured application data.
- Defensively recovers JSON object strings while rejecting plain text and already-encoded SAGE semantic envelopes.
- Applies the same structured-content boundary to the OpenClaw adapter.
- Ships a standalone Hermes plugin that does not require package installation inside Hermes.
- Adds direct source-checkout and GitHub release install paths for Hermes and OpenClaw.
- Adds workspace-aware `sage-integrate` output and release-asset guidance.
- Adds regression coverage for the adapter boundary found during live Hermes integration testing.
