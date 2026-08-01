# SAGE v0.2.3

Vendor-neutral semantic communication runtime and durable context bus for AI agents.

**Protocol `sage/0.2` · wire version `2` · migration baseline `0001_sage_0_2` · 13 TCK vectors** — unchanged from v0.2.2.

## What's new

- **Concurrency-safe receiver knowledge store** — `ensure()` and `_add_value()` no longer race on the `uq_receiver_knowledge` constraint under concurrent load (previously surfaced as `IntegrityError` in the configured-database qualification run).
- **Restored green CI pipeline** — the full matrix (Python 3.11–3.14, PostgreSQL, OpenClaw adapter, packaging, dependency audit, staging cluster) now passes on every run:
  - `release_check.py` gate ordering fixed (OpenClaw `dist` built before the check; `node_modules`/caches cleaned).
  - Stale `0.2.2` artifact names corrected across the package and OpenClaw jobs.
  - Staging PostgreSQL volume mount fixed for the postgres 18 image (`/var/lib/postgresql`), and `migrate` now runs before the cluster is declared healthy.
  - Staging recovery verification uses the real ack endpoint (`/v1/bus/{message_id}/ack`) and stop-based worker failover with bounded retries.
- **`mcp` extra pinned to `mcp>=1.9,<2`** — the `sage-mcp` FastMCP integration builds again (mcp 2.x removed `mcp.server.fastmcp`).
- **Robust latency gate** — warmup, top-1% outlier trimming, and best-of-2 measurement rounds with the same absolute limits, so shared-runner noise no longer flakes the gate.
- Known limitation documented in [Issue #11](https://github.com/NeuralBinary/SAGE/issues/11): the mcp SDK's streamable session manager is single-run per process; pytest phases run without the `mcp` extra and MCP is qualified via the package job's `build_server()` assertion.

## Install

```bash
# Python wheel (Python 3.11+)
python -m pip install https://github.com/NeuralBinary/SAGE/releases/download/v0.2.3/sage_agent_protocol-0.2.3-py3-none-any.whl

# Hermes Agent plugin
# Download sage-hermes-plugin-v0.2.3.zip from this release, then:
unzip sage-hermes-plugin-v0.2.3.zip
# follow the plugin's install.sh

# OpenClaw plugin
# Download sage-agent-openclaw-sage-0.2.3.tgz from this release, then:
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.3.tgz
```

Production deployments require PostgreSQL; see `docker-compose.quickstart.yml` and `deploy/staging/compose.yml`.

## Assets

| Asset | Purpose |
| --- | --- |
| `sage_agent_protocol-0.2.3-py3-none-any.whl` | Python wheel |
| `sage-plugin-v0.2.3.zip` | Source archive |
| `sage-hermes-plugin-v0.2.3.zip` | Hermes Agent plugin |
| `sage-agent-openclaw-sage-0.2.3.tgz` | OpenClaw plugin |
| `SAGE-v0.2.3-VERIFICATION.md` | Release verification report |
| `SAGE-v0.2.3-SHA256SUMS.txt` | Asset checksums |

## Upgrade / rollback

- Upgrade: `python -m pip install --upgrade sage_agent_protocol` (or reinstall from the wheel above). No schema changes: the `0001_sage_0_2` migration baseline is unchanged.
- Rollback: reinstall the v0.2.2 wheel (`sage_agent_protocol-0.2.2-py3-none-any.whl` from the [v0.2.2 release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.2)).
