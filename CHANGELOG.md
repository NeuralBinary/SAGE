# Changelog

## 0.2.4

- Patch release over 0.2.3. Protocol `sage/0.2`, wire version `2`, migration baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.
- Fixes the MCP integration for repeated application startups (Issue #11): the FastMCP server is now built fresh on every app lifespan behind a stable delegating mount at `/mcp`, with an owner-guarded live-install stack so overlapping lifespans hand the mount back instead of clobbering it. Repeated app startups with the `mcp` extra now work, and pytest phases plus the release workflow install `[dev,mcp,bench,otel]` again.
- Hardens the latency gate on shared CI runners: `--best-of 3` rounds (was best-of-2), with all limits unchanged.
- Ships the wiki-styled GitHub Pages documentation site (MkDocs Material: sidebar navigation, search, dark mode) as the project's public docs.
- Updates documentation, release artifacts, and verification status for v0.2.4.

## 0.2.3

- Patch release over 0.2.2. Protocol `sage/0.2`, wire version `2`, migration baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.
- Fixes a concurrency race in the receiver knowledge store: `ensure()` and `_add_value()` are now race-safe (savepoint + integrity handling), eliminating `IntegrityError: duplicate key ... uq_receiver_knowledge` under concurrent qualification load (PostgreSQL and SQLite).
- Restores the CI pipeline to green: fixes `release_check.py` ordering (OpenClaw `dist` built before the check, `node_modules`/caches cleaned), stale `0.2.2` artifact names in the package/openclaw jobs, the staging PostgreSQL volume mount for the postgres 18 image, and the staging recovery verification (correct `/v1/bus/{message_id}/ack` endpoint; stop-based worker failover; bounded retries for load-balancer failover).
- Pins the `mcp` extra to `mcp>=1.9,<2` so `sage-mcp`'s FastMCP integration builds again (mcp 2.x removed `mcp.server.fastmcp`).
- Makes the latency gate robust on shared CI runners: steady-state sampling (warmup, outlier trimming, best-of-2 rounds) with unchanged limits.
- Documents the mcp streamable-session-manager single-run limitation (Issue #11) and keeps pytest phases on `[dev]`; MCP is qualified via the package job's `build_server()` assertion.
- Updates documentation, release artifacts, and verification status for v0.2.3.

## 0.2.1

- Keeps protocol `sage/0.2`, wire version `2`, and migration baseline `0001_sage_0_2` unchanged.
- Constrains Hermes `sage_handoff.content` to raw structured application data.
- Defensively recovers JSON object strings while rejecting plain text and already-encoded SAGE semantic envelopes.
- Applies the same structured-content boundary to the OpenClaw adapter.
- Ships a standalone Hermes plugin that does not require package installation inside Hermes.
- Adds direct source-checkout and GitHub release install paths for Hermes and OpenClaw.
- Adds workspace-aware `sage-integrate` output and release-asset guidance.
- Adds regression coverage for the adapter boundary found during live Hermes integration testing.
