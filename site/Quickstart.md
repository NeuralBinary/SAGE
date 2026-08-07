
# Quickstart

SAGE has one service and multiple agent adapters. Start the service, verify it, then connect Hermes, OpenClaw, Python, REST, A2A, or MCP.

## Docker quickstart (easiest)

Requirements: Docker with the Compose plugin.

Linux/macOS:

```bash
./quickstart.sh
```

Windows PowerShell:

```powershell
.\quickstart.ps1
```

This starts a local SAGE service at `http://127.0.0.1:8080`, persists data in a named Docker volume (`sage_quickstart_data`), waits for health, and runs an end-to-end delivery check. Interactive API documentation is at `http://127.0.0.1:8080/docs`.

Useful commands:

```bash
docker compose -f docker-compose.quickstart.yml logs -f sage
docker compose -f docker-compose.quickstart.yml exec -T sage sage-doctor
docker compose -f docker-compose.quickstart.yml exec -T sage sage-demo
docker compose -f docker-compose.quickstart.yml exec -T sage sage-demo --single-agent
docker compose -f docker-compose.quickstart.yml down
```

Add `-v` to the final command only when you intentionally want to delete local SAGE data.

The quickstart Compose file runs SAGE in development mode with a SQLite database at `/data/sage.db` inside the volume and authentication disabled. It is intended for evaluation and trusted local development only — see [Production](Production.md) for the fail-closed production topology.

## Python release install

Python 3.11 or newer is required. Install the v0.2.6 release wheel directly from the GitHub release:

```bash
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install https://github.com/NeuralBinary/SAGE/releases/download/v0.2.6/sage_agent_protocol-0.2.6-py3-none-any.whl
```

Start a local service with authentication disabled **only on a trusted interface**:

```bash
export SAGE_AUTH_REQUIRED=false  # PowerShell: $env:SAGE_AUTH_REQUIRED="false"
sage-api
```

`sage-api` serves on `0.0.0.0:8080`.

> **Note on the default database:** with no `SAGE_DATABASE_URL` set, the service uses `sqlite:///$HOME/sage.db` — the current user's **home directory**, independent of the working directory (fixed in v0.2.2; previously the default was working-directory-relative and could fail from a read-only directory). An explicit `SAGE_DATABASE_URL` is always authoritative and is preserved exactly. Production requires PostgreSQL; see [Configuration](Configuration.md) and [Production](Production.md).

## Verify the service

From another terminal:

```bash
sage-doctor
sage-demo --single-agent
```

Or with an explicit URL:

```bash
sage-doctor --url http://127.0.0.1:8080
sage-demo --url http://127.0.0.1:8080 --single-agent
```

- `sage-doctor` checks liveness, database readiness, `sage/0.2` wire identity, handoff, context claim, ACK, and removal from the pending mailbox.
- `sage-demo --single-agent` sends, decodes, and acknowledges one message to itself, exercising the same durable lifecycle as two-agent delivery.

## Install the Hermes plugin

Download `sage-hermes-plugin-v0.2.6.zip` from the [v0.2.6 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.6), then:

```bash
unzip sage-hermes-plugin-v0.2.6.zip
cd sage-hermes-plugin-v0.2.6
./install.sh
```

Windows PowerShell:

```powershell
Expand-Archive .\sage-hermes-plugin-v0.2.6.zip
cd .\sage-hermes-plugin-v0.2.6
.\install.ps1
```

The installer copies the plugin to `$HERMES_HOME/plugins/sage` (or `~/.hermes/plugins/sage` when `HERMES_HOME` is not set) and enables it when the `hermes` command is available.

Set these variables in the environment used to start Hermes:

```text
SAGE_URL=http://127.0.0.1:8080
SAGE_AGENT_ID=hermes-a
SAGE_WORKSPACE=default
SAGE_API_KEY=
SAGE_MAX_INJECT_TOKENS=1200
```

`SAGE_API_KEY` is needed only when the SAGE service requires authentication. Use a unique `SAGE_AGENT_ID` for each agent that has a separate mailbox. Verify with `hermes plugins list --plain` — `sage` should appear as enabled. Start a new Hermes session after changing plugin files or environment variables.

Full Docker and Windows instructions are in `integrations/hermes/README.md`. See also [Adapters](Adapters.md).

## Install the OpenClaw plugin

Download `sage-agent-openclaw-sage-0.2.6.tgz` from the [v0.2.6 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.6), then install the native plugin:

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.6.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

For noninteractive installs, OpenClaw may require `--force` for a reviewed local archive or npm-pack source.

Configure the plugin:

```json
{
  "url": "http://127.0.0.1:8080",
  "agentId": "openclaw-a",
  "workspace": "default",
  "apiKey": "",
  "autoInject": true,
  "maxInjectTokens": 1200,
  "contextBudgetFraction": 0.2
}
```

Use a unique `agentId` for every agent that has a separate SAGE mailbox; set `apiKey` only when the SAGE service requires authentication. Verify the service independently with `sage-doctor --url http://127.0.0.1:8080 --agent-id openclaw-a`. See [Adapters](Adapters.md).

## Custom agents (REST/Python)

The durable lifecycle is:

```text
handoff -> pending -> claimed -> acknowledged
                       |
                       +-> lease expiry -> claimable again
```

- Send raw application-level JSON to `POST /v1/bus/handoff`.
- Claim already-decoded context from `GET /v1/bus/context/{receiver}` and ACK it only after successful consumption (via `POST /v1/bus/{message_id}/ack` or the batched `POST /v1/bus/ack-batch`).
- Adapters must **not** construct SAGE semantic envelopes themselves — semantic encoding is owned by SAGE.

Discover generated integration settings with:

```bash
sage-integrate --list
sage-integrate hermes --url http://127.0.0.1:8080 --agent-id hermes-a
sage-integrate openclaw --url http://127.0.0.1:8080 --agent-id claw-a
```

Local unauthenticated mode is only for a trusted local interface. Production settings are documented in [Configuration](Configuration.md), [Production](Production.md), and the repo's `docs/SECURITY.md` and `docs/OPERATIONS.md`.

Next: [Configuration](Configuration.md)
