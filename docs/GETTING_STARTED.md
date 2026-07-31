# Getting started

SAGE has one runtime and multiple adapter surfaces. Start the runtime once, then connect any supported agent host to the same service.

## Choose an install path

| Target | Source checkout | GitHub release asset |
| --- | --- | --- |
| SAGE runtime | `python -m pip install -e .` | `python -m pip install ./sage_agent_protocol-0.2.1-py3-none-any.whl` |
| Hermes Agent | `./integrations/hermes/install.sh` | `sage-hermes-plugin-v0.2.1.zip` |
| OpenClaw | `openclaw plugins install --link ./integrations/openclaw` | `sage-agent-openclaw-sage-0.2.1.tgz` |
| Python/custom runtime | import `SageRuntime` from the checkout | install the wheel |
| A2A peer | `sage_plugin.a2a_adapter` | wheel or REST binding |
| MCP client | `/mcp` | deployed SAGE service |
| REST client | `/v1/*` | deployed SAGE service |

## Run SAGE locally

Python 3.11 or newer is required.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
export SAGE_AUTH_REQUIRED=false
sage-api
```

Verify the service:

```bash
curl -sS http://127.0.0.1:8080/health/live
curl -sS http://127.0.0.1:8080/v1/ready
curl -sS http://127.0.0.1:8080/v1/protocol
```

Local unauthenticated mode is for a trusted local interface. Production configuration is documented in `docs/CONFIGURATION.md`, `docs/SECURITY.md`, and `docs/OPERATIONS.md`.

## Hermes Agent

The standalone Hermes plugin does not require SAGE to be installed into Hermes Python.

```bash
./integrations/hermes/install.sh
export SAGE_URL=http://127.0.0.1:8080
export SAGE_AGENT_ID=hermes-a
export SAGE_WORKSPACE=default
hermes plugins enable sage
```

For the official Docker image, install into the host directory mounted at `/opt/data`, pass the SAGE variables to the container, and use a host gateway or shared Docker network to reach SAGE. Full steps are in `integrations/hermes/README.md`.

## OpenClaw

From source:

```bash
cd integrations/openclaw
npm install
npm run build
cd ../..
openclaw plugins install --link ./integrations/openclaw
openclaw plugins enable sage
```

From a GitHub release:

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.1.tgz
openclaw plugins enable sage
```

Full configuration is in `integrations/openclaw/README.md`.

## Custom runtimes

The durable transport surface is HTTP and the Python runtime API. The standard bus lifecycle is:

```text
handoff -> pending -> claimed -> acked
                       |
                       +-> lease expiry -> claimable again
```

Use `/v1/bus/handoff` to send raw application data and `/v1/bus/context/{receiver}` when the host can inject peer context before a model turn. ACK only after successful consumption.

## Integration discovery

After installing the Python package:

```bash
sage-integrate --list
sage-integrate hermes --url http://127.0.0.1:8080 --agent-id hermes-a
sage-integrate openclaw --url http://127.0.0.1:8080 --agent-id claw-a
```

SAGE owns semantic encoding, references, state, deltas, receiver knowledge, persistence, and delivery semantics. Adapters should pass raw structured application data rather than constructing SAGE wire objects themselves.
