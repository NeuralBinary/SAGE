# Integration model

## Recommended order

1. Native hook/plugin adapter when the framework offers a safe lifecycle extension point.
2. A2A as the primary generic envelope when independent agent runtimes communicate as peers.
3. MCP for model/tool/context access and compatibility.
4. REST/Python runtime for custom orchestrators.

The SAGE server stays the same in all cases.

## Hermes

The Python package exposes `hermes_agent.plugins:sage`. The plugin registers a handoff tool plus pre/post LLM hooks. Pre-LLM claims mailbox messages within an injection budget; post-LLM ACKs only successful-turn claims. A crashed turn is recovered by the bus claim lease.

Environment: `SAGE_URL`, `SAGE_AGENT_ID`, `SAGE_WORKSPACE`, `SAGE_API_KEY`, `SAGE_MAX_INJECT_TOKENS`.

## OpenClaw

`integrations/openclaw` is a native mixed tool/hook plugin. `agent_turn_prepare` claims and injects a decoded SAGE context batch; `agent_end` ACKs that batch only after a successful run. The plugin adapts its injection budget to OpenClaw's exposed context token budget when present.

Third-party prompt-mutating/conversation hooks must be enabled according to the host's plugin security settings.

## Claude / OpenAI / generic MCP

Use the same remote `/mcp` endpoint. MCP tools include `sage_handoff`, `sage_poll`, `sage_ack`, `sage_send`, `sage_receive`, refs, state, codebooks, evals, and latent transport.

Because MCP authentication is service-scoped in v0.2, use a per-agent gateway/native adapter when mailbox isolation between untrusted agents is required.

## Generic A2A

Use `sage_plugin.a2a_adapter.pack_data_part` / `unpack_data_part` or the REST bridge. The payload is provider-neutral. A2A task/message lifecycle and agent cards remain owned by the chosen A2A SDK/runtime.

## Custom orchestrator

Use `SageRuntime.handoff/poll/ack` directly. This is the smallest dependency surface and avoids model-visible tool calls entirely.


## Protocol boundaries

SAGE core does not import MCP. `scripts/architecture_check.py` enforces the adapter boundary. A2A carries SAGE structured data while retaining discovery, task/message lifecycle, streaming, cancellation, and collaboration semantics. SAGE owns the semantic payload, references, state/deltas, learned vocabulary, durable context, provenance, and receiver knowledge.

The same wire packet must keep identical canonical MessagePack identity whether carried by a native adapter, A2A, MCP, REST, queue, or custom transport.
