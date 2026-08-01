# SAGE v0.2.4

Patch release over v0.2.3. Protocol `sage/0.2`, wire version `2`, migration
baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.

## What's new in v0.2.4

- **Per-lifespan MCP server (Issue #11).** The MCP integration no longer breaks
  on repeated application startups. The FastMCP server is built fresh on every
  app lifespan behind a stable delegating mount at `/mcp`, with an
  owner-guarded live-install stack so an exiting lifespan hands the mount back
  to a still-running overlapping lifespan instead of clobbering it. Repeated
  app startups with the `mcp` extra now work, and the pytest phases and release
  workflow install `[dev,mcp,bench,otel]` again.
  See https://github.com/NeuralBinary/SAGE/issues/11
- **Latency-gate robustness.** The CI latency gate now uses `--best-of 3`
  rounds (was best-of-2) on shared runners, with all limits unchanged.
- **Documentation site.** The docs are published as a wiki-styled GitHub Pages
  site (MkDocs Material: sidebar navigation, search, dark mode).

## Install

### Python wheel

Python 3.11 or newer is required. Download the wheel from the
[v0.2.4 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.4),
then install it and start a local service with authentication disabled only on
a trusted interface:

```bash
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install https://github.com/NeuralBinary/SAGE/releases/download/v0.2.4/sage_agent_protocol-0.2.4-py3-none-any.whl
export SAGE_AUTH_REQUIRED=false  # PowerShell: $env:SAGE_AUTH_REQUIRED="false"
sage-api
```

Then verify with `sage-doctor` and `sage-demo --single-agent`.

### Hermes plugin

Download `sage-hermes-plugin-v0.2.4.zip` from the
[v0.2.4 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.4),
then install the plugin:

```bash
unzip sage-hermes-plugin-v0.2.4.zip
cd sage-hermes-plugin-v0.2.4
./install.sh
```

### OpenClaw plugin

Download `sage-agent-openclaw-sage-0.2.4.tgz` from the
[v0.2.4 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.4),
then install the native plugin:

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.4.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

## Release assets

| Asset | Description |
| --- | --- |
| `sage-plugin-v0.2.4.zip` | Source archive |
| `sage-hermes-plugin-v0.2.4.zip` | Hermes plugin |
| `sage_agent_protocol-0.2.4-py3-none-any.whl` | Python wheel |
| `sage-agent-openclaw-sage-0.2.4.tgz` | OpenClaw plugin |
| `SAGE-v0.2.4-VERIFICATION.md` | Verification report |
| `SAGE-v0.2.4-SHA256SUMS.txt` | SHA-256 checksums |

## Upgrade and rollback

Upgrade from v0.2.3 by installing the v0.2.4 wheel and refreshing the Hermes
and OpenClaw plugins from this release. The protocol, wire version, migration
baseline, and TCK vectors are unchanged, so no data migration is required.

To roll back, reinstall the v0.2.3 wheel
(`sage_agent_protocol-0.2.3-py3-none-any.whl` from the
[v0.2.3 release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.3))
and re-extract the v0.2.3 Hermes and OpenClaw plugins over the current ones.
