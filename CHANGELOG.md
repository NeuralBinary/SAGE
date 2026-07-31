# Changelog

## 0.2.1

- Keeps protocol `sage/0.2`, wire version `2`, and migration baseline `0001_sage_0_2` unchanged.
- Constrains Hermes `sage_handoff.content` to raw structured application data.
- Defensively recovers JSON object strings while rejecting plain text and already-encoded SAGE semantic envelopes.
- Applies the same structured-content boundary to the OpenClaw adapter.
- Ships a standalone Hermes plugin that does not require package installation inside Hermes.
- Adds direct source-checkout and GitHub release install paths for Hermes and OpenClaw.
- Adds workspace-aware `sage-integrate` output and release-asset guidance.
- Adds regression coverage for the adapter boundary found during live Hermes integration testing.
