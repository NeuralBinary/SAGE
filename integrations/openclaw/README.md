# SAGE OpenClaw adapter

This native plugin exposes SAGE bus tools, claims cross-agent handoffs in `agent_turn_prepare`, and ACKs them from `agent_end` only when OpenClaw reports a successful run. Failed/unknown runs are left for lease-based redelivery.

Install the packaged adapter with OpenClaw's deterministic local npm-pack source:

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.1.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

Because the adapter uses `agent_turn_prepare` and `agent_end`, a trusted non-bundled install must permit conversation access; prompt injection must also be enabled. Configure the `sage` plugin entry with `allowConversationAccess: true` and do not set `allowPromptInjection: false`.

Set plugin config for `url`, `agentId`, `workspace`, `apiKey`, `autoInject`, `maxInjectTokens`, and `contextBudgetFraction`.
