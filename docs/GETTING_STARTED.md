# Getting started

SAGE has one service and multiple agent adapters. Start the service, verify it,
then connect Hermes, OpenClaw, Python, REST, A2A, or MCP.

## Fastest local setup

Requirements: Docker with the Compose plugin.

Linux/macOS:

```bash
./quickstart.sh
```

Windows PowerShell:

```powershell
.\quickstart.ps1
```

This starts a local SAGE service at `http://127.0.0.1:8080`, persists data in a
Docker volume, waits for health, and runs an end-to-end delivery check.
Interactive API documentation is at `http://127.0.0.1:8080/docs`.

Useful commands:

```bash
docker compose -f docker-compose.quickstart.yml logs -f sage
docker compose -f docker-compose.quickstart.yml exec -T sage sage-doctor
docker compose -f docker-compose.quickstart.yml exec -T sage sage-demo
docker compose -f docker-compose.quickstart.yml exec -T sage sage-demo --single-agent
docker compose -f docker-compose.quickstart.yml down
```

Add `-v` to the final command only when you intentionally want to delete local
SAGE data.

## Install the Python release

Python 3.11 or newer is required.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install ./sage_agent_protocol-0.2.2-py3-none-any.whl
export SAGE_AUTH_REQUIRED=false
sage-api
```

PowerShell activation and environment variable:

```powershell
.\.venv\Scripts\Activate.ps1
$env:SAGE_AUTH_REQUIRED = "false"
sage-api
```

Verify from another terminal:

```bash
sage-doctor --url http://127.0.0.1:8080
sage-demo --url http://127.0.0.1:8080
```

Local unauthenticated mode is only for a trusted local interface. Production
settings are documented in `CONFIGURATION.md`, `SECURITY.md`, and
`OPERATIONS.md`.

## Connect Hermes

```bash
unzip sage-hermes-plugin-v0.2.2.zip
cd sage-hermes-plugin-v0.2.2
./install.sh
```

Set `SAGE_URL`, `SAGE_AGENT_ID`, and `SAGE_WORKSPACE` in the environment used to
start Hermes. Set `SAGE_API_KEY` when authentication is enabled. Full Docker and
Windows instructions are in `integrations/hermes/README.md`.

## Connect OpenClaw

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.2.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

Configure `url`, `agentId`, `workspace`, and optionally `apiKey`. Full details
are in `integrations/openclaw/README.md`.

## Custom agents

The durable lifecycle is:

```text
handoff -> pending -> claimed -> acknowledged
                       |
                       +-> lease expiry -> claimable again
```

Send raw application-level JSON to `/v1/bus/handoff`. Claim already-decoded
context from `/v1/bus/context/{receiver}` and ACK it only after successful
consumption. Adapters must not construct SAGE semantic envelopes themselves.

Discover generated integration settings with:

```bash
sage-integrate --list
sage-integrate hermes --url http://127.0.0.1:8080 --agent-id hermes-a
sage-integrate openclaw --url http://127.0.0.1:8080 --agent-id claw-a
```
