# Security model

SAGE separates transport authentication, agent identity, object authorization, semantic integrity, and model trust. No one control is treated as a substitute for the others.

## Production startup policy

`SAGE_ENV=production` activates fail-closed validation. Production startup is rejected unless authentication is enabled, service credentials are present, a server database is configured, automatic schema creation is disabled, explicit allowed hosts are provided, and interactive API documentation is disabled.

Service API keys and agent API keys must contain at least 32 characters. Service and agent credentials may not share the same secret value.

## Credentials and identity

`SAGE_API_KEYS` contains service/control-plane credentials. These credentials authorize administrative API operations and the mounted MCP surface.

`SAGE_AGENT_KEYS` is a JSON object whose keys are credentials and whose values bind each credential to an agent identity or workspace/agent identity. Agent-scoped requests cannot override the authenticated actor through request fields.

Agent credentials are enforced on mailbox access, handoffs, references, semantic facts, routing, and Inspector access. Administrative concept/federation operations require service identity.

Credential storage, distribution, rotation, revocation, and audit are operator responsibilities. Secrets should be delivered through the deployment platform's secret mechanism and must not be committed to the repository.

## HTTP protections

Production uses explicit Host allowlisting through `TrustedHostMiddleware`. Interactive documentation and OpenAPI exposure are disabled. `/metrics` requires service authentication unless `SAGE_METRICS_PUBLIC=true` is intentionally configured. `/health/live` remains unauthenticated for liveness infrastructure.

The request-body middleware enforces `SAGE_HTTP_MAX_BODY_BYTES` for declared and streamed bodies. API/MCP responses receive `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`; `/v1` and `/mcp` responses receive `Cache-Control: no-store`.

TLS should terminate at a trusted ingress or reverse proxy. Learned embedding endpoints used in production must use HTTPS.

## Content-addressed references

Reference identity is derived from content with a URI beginning `sage:sha256:` followed by a full lowercase SHA-256 digest. Object identity is independent of access policy.

Authorization policy is stored in reference grants and includes workspace, owner, ACL, allowed field paths, memory tier, TTL, provenance, and invalidation state. Identical content can therefore deduplicate globally without receiving global authorization.

Selective resolution enforces the grant's allowed field paths. Zero-copy forwarding creates receiver access to the existing object while retaining those restrictions.

AES-GCM at-rest protection is enabled by providing a URL-safe base64 value that decodes to exactly 32 bytes through `SAGE_REF_ENCRYPTION_KEY`. Set `SAGE_REQUIRE_REF_ENCRYPTION=true` when unencrypted reference storage must be rejected.

Encryption-key rotation and re-encryption are operator-controlled in v0.2.

## Packet and federation signatures

SAGE uses Ed25519 for packet signatures. Signing keys are URL-safe base64 encodings of raw 32-byte keys. `SAGE_REQUIRE_PACKET_SIGNATURES=true` requires a verification public key at startup and causes unsigned or invalid packets to fail closed.

Signatures cover canonical MessagePack bytes with the signature field omitted from the signed body. The signature establishes integrity and origin for the configured key; application authorization remains separate.

Federation peers may have independent verification keys and namespace allowlists. Imported semantic structures are observed under local lifecycle rules rather than becoming trusted active vocabulary solely because a peer supplied them.

## Semantic safety

The semantic-loss firewall preserves high-impact meaning when semantic confidence is insufficient. Critical values include negation, amounts, identity, authorization, deadlines, environment markers, instructions, and constraints.

Epistemic classification prevents predictions, hypotheses, instructions, observations, and preferences from silently becoming facts. Contradictory claims retain both sides with provenance and confidence. Dependency edges allow derived knowledge to be invalidated when a source is no longer valid.

Pattern activation requires counterfactual validation by default. Receiver/model-specific fidelity can disable an otherwise active pattern for one peer without disabling it globally.

## Durable delivery

Delivery is at-least-once. Claims are leases. A failed or terminated consumer that does not acknowledge a claim leaves the message eligible for redelivery after lease expiry. Successful consumers acknowledge by message ID. Batch acknowledgement is available to reduce network fan-out.

Downstream side effects must be idempotent using `message_id` or `correlation_id`.

## Telemetry

Prometheus and OpenTelemetry measurements should contain protocol and numeric metadata only. Raw user/model content should not be placed into telemetry attributes. Access to telemetry endpoints and exporters should follow the same network segmentation policy as other operational data.

## Threat boundary

SAGE does not make untrusted model output safe. Prompt injection, malicious tool output, authorization of real-world actions, policy enforcement, provider security, and host-runtime integrity remain separate responsibilities.
