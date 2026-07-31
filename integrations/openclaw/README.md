# SAGE for OpenClaw

The native OpenClaw plugin exposes SAGE handoff tools, injects claimed peer context during turn preparation, and ACKs it only after OpenClaw reports a successful run.

## Source checkout

Build the adapter once, then install or link the local plugin directory:

```bash
cd integrations/openclaw
npm install
npm run build
cd ../..
openclaw plugins install --link ./integrations/openclaw
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

## GitHub release asset

Install the packed release asset:

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.1.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

For noninteractive installs, OpenClaw can require `--force` for a reviewed local archive or npm-pack source.

Configure `url`, `agentId`, `workspace`, `apiKey`, `autoInject`, `maxInjectTokens`, and `contextBudgetFraction`, or use `SAGE_URL`, `SAGE_AGENT_ID`, `SAGE_WORKSPACE`, and `SAGE_API_KEY` where applicable.

`sage_handoff.content` is structured application data. The adapter rejects SAGE semantic envelopes and prevents the model from owning wire encoding.
