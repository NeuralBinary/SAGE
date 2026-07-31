# Configuration reference

SAGE configuration uses environment variables with the `SAGE_` prefix. Names below use their full environment form. Development defaults favor local operation; production mode applies additional fail-closed validation.

## Runtime and database

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_ENV` | `development` | Runtime environment. `production` enables strict startup validation. |
| `SAGE_DATABASE_URL` | `sqlite:///./sage.db` | SQLAlchemy database URL. Production rejects SQLite. |
| `SAGE_DB_POOL_SIZE` | `10` | Server-database connection pool size. |
| `SAGE_DB_MAX_OVERFLOW` | `20` | Additional pooled connections allowed above pool size. |
| `SAGE_DB_POOL_TIMEOUT_SECONDS` | `30` | Maximum pool wait time. |
| `SAGE_DB_POOL_RECYCLE_SECONDS` | `1800` | Connection recycle interval. |
| `SAGE_AUTO_CREATE_SCHEMA` | `true` | Development schema creation. Production requires `false` and Alembic migrations. |

## Authentication and HTTP

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_AUTH_REQUIRED` | `false` | Enables bearer authentication. Production requires `true`. |
| `SAGE_API_KEYS` | empty | Comma-separated service keys. Each configured key must contain at least 32 characters when auth is enabled. |
| `SAGE_AGENT_KEYS` | empty | JSON mapping from secret key to `agent` or `workspace:agent` scope. |
| `SAGE_ALLOWED_HOSTS` | empty | Comma-separated Host allowlist. Production requires explicit entries. |
| `SAGE_DOCS_ENABLED` | `true` | Exposes interactive docs/OpenAPI. Production requires `false`. |
| `SAGE_METRICS_PUBLIC` | `false` | Allows unauthenticated Prometheus metrics when intentionally enabled. |
| `SAGE_HTTP_MAX_BODY_BYTES` | `52428800` | Maximum HTTP request body size. |

## Payload and token budgets

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_MAX_INLINE_BYTES` | `2048` | Inline-content threshold before reference-backed handling. |
| `SAGE_MAX_INPUT_BYTES` | `50000000` | Maximum input payload size accepted by the semantic encoder. |
| `SAGE_MAX_STORE_BYTES` | `50000000` | Maximum stored reference content size. |
| `SAGE_MAX_PACKET_BYTES` | `8192` | Packet-size target/limit used by transport decisions. |
| `SAGE_DEFAULT_TOKEN_BUDGET` | `1200` | Default receiver context budget. |
| `SAGE_CHARS_PER_TOKEN_ESTIMATE` | `4.0` | Deterministic estimate used when exact tokenizer data is unavailable. |
| `SAGE_MAX_MESSAGE_ATOMS` | `256` | Maximum semantic atoms in a message. |

## Semantic compiler and codebooks

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_SEMANTIC_THRESHOLD` | `0.93` | Similarity threshold for semantic matching. |
| `SAGE_SEMANTIC_LOSSLESS_THRESHOLD` | `0.985` | Higher confidence required before discarding original surface text. |
| `SAGE_SEMANTIC_LSH_BITS` | `10` | Bit width used by deterministic locality-sensitive-hash buckets for large vocabularies. |
| `SAGE_SEMANTIC_LSH_HAMMING` | `1` | Neighbor Hamming radius used for bounded large-vocabulary lookup. |
| `SAGE_SEMANTIC_CANDIDATE_LIMIT` | `512` | Maximum fuzzy candidates evaluated after LSH filtering. |
| `SAGE_SEMANTIC_FUZZY_SCAN_LIMIT` | `1000` | Vocabulary size below which exhaustive fuzzy comparison remains permitted. |
| `SAGE_SEMANTIC_FIREWALL_ENABLED` | `true` | Enables critical-semantic preservation. |
| `SAGE_CRITICAL_SEMANTIC_THRESHOLD` | `0.999` | Preservation threshold for high-impact semantics. |
| `SAGE_CODEBOOK` | `global` | Active codebook namespace. |
| `SAGE_CORE_CODEBOOK` | `core` | Core namespace. |
| `SAGE_PROMOTION_MIN_COUNT` | `8` | Individual concept observation threshold. |
| `SAGE_PROMOTION_MIN_SAVINGS_BYTES` | `64` | Required estimated savings for concept promotion. |
| `SAGE_PROMOTION_MAX_NEIGHBOR_SIMILARITY` | `0.88` | Ambiguity guard during concept promotion. |

## Pattern learning

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_LEARNING_MODE` | `observe` | Serving mode records evidence without promoting vocabulary. `managed` allows controlled promotion workflows. |
| `SAGE_PATTERN_LEARNING_ENABLED` | `true` | Enables persistent higher-order pattern learning. |
| `SAGE_PATTERN_STRING_CONSTANTS_ENABLED` | `false` | Allows string literals to become stable template constants. Disabled by default to reduce accidental identity/PII vocabulary. |
| `SAGE_PATTERN_MIN_COMPONENTS` | `2` | Minimum components in a learned pattern. |
| `SAGE_PATTERN_MAX_COMPONENTS` | `6` | Maximum components in a learned pattern. |
| `SAGE_PATTERN_MAX_OBSERVATIONS_PER_MESSAGE` | `64` | Observation work bound per message. |
| `SAGE_PATTERN_CANDIDATE_MIN_COUNT` | `4` | Candidate frequency threshold. |
| `SAGE_PATTERN_MIN_SAVINGS_BYTES` | `64` | Candidate savings threshold. |
| `SAGE_PATTERN_SHADOW_MIN_SAMPLES` | `3` | Minimum shadow feedback samples. |
| `SAGE_PATTERN_SHADOW_MIN_SUCCESS` | `0.95` | Minimum shadow success rate. |
| `SAGE_PATTERN_AUTO_ACTIVATE` | `true` | Allows activation after all configured gates pass. |
| `SAGE_PATTERN_CANDIDATE_RETENTION_DAYS` | `30` | Candidate retention period. |
| `SAGE_PATTERN_RECURSIVE_LEARNING_ENABLED` | `true` | Enables parent/child pattern composition. |
| `SAGE_PATTERN_UTILITY_MIN_SCORE` | `0.5` | Minimum utility score for promotion. |
| `SAGE_PATTERN_COUNTERFACTUAL_REQUIRED` | `true` | Requires full-vs-compressed validation before activation. |
| `SAGE_PATTERN_COUNTERFACTUAL_MIN_SAMPLES` | `3` | Minimum counterfactual samples. |
| `SAGE_PATTERN_COUNTERFACTUAL_MIN_FIDELITY` | `0.99` | Minimum semantic fidelity for activation. |
| `SAGE_PATTERN_RECEIVER_MIN_FIDELITY` | `0.95` | Receiver/model minimum fidelity for emission. |
| `SAGE_PATTERN_GC_COOLING_DAYS` | `30` | Inactivity before active vocabulary cools. |
| `SAGE_PATTERN_GC_RETIRE_DAYS` | `90` | Inactivity before cooling vocabulary retires. |
| `SAGE_PATTERN_NAMESPACE_PROMOTION_MIN_UTILITY` | `0.95` | Minimum utility for broader namespace promotion. |
| `SAGE_PATTERN_TRUST_REQUIRED` | `true` | Requires trusted source evidence before promotion/activation. |
| `SAGE_PATTERN_MIN_SOURCE_DIVERSITY` | `2` | Global lower bound for distinct source evidence. |
| `SAGE_PATTERN_MAX_SOURCE_SHARE` | `0.75` | Maximum share of evidence attributable to one source. |
| `SAGE_PATTERN_MIN_TRUST_SCORE` | `0.6` | Minimum weighted source trust. |
| `SAGE_PATTERN_DEFAULT_TRUST_SCOPE` | `session` | Default learning trust scope. |
| `SAGE_PATTERN_SESSION_MIN_SOURCES` | `2` | Distinct trusted sources required for session scope. |
| `SAGE_PATTERN_PROJECT_MIN_SOURCES` | `3` | Distinct trusted sources required for project scope. |
| `SAGE_PATTERN_WORKSPACE_MIN_SOURCES` | `4` | Distinct trusted sources required for workspace scope. |
| `SAGE_PATTERN_DOMAIN_MIN_SOURCES` | `6` | Distinct trusted sources required for domain scope. |
| `SAGE_PATTERN_FEDERATION_MIN_SOURCES` | `8` | Distinct trusted sources required for federation scope. |
| `SAGE_CALIBRATION_BUCKETS` | `10` | Reliability calibration buckets. |
| `SAGE_CALIBRATION_MIN_SAMPLES` | `20` | Samples before receiver calibration is treated as mature evidence. |
| `SAGE_CALIBRATION_MAX_ECE` | `0.08` | Maximum expected calibration error allowed by activation policy. |
| `SAGE_PATTERN_HOLDOUT_MIN_SAMPLES` | `5` | Minimum holdout observations before activation. |
| `SAGE_PATTERN_HOLDOUT_MIN_SOURCES` | `3` | Minimum distinct holdout validation sources before activation. |
| `SAGE_PATTERN_HOLDOUT_MIN_FIDELITY` | `0.995` | Minimum holdout semantic fidelity. |
| `SAGE_PATTERN_DRIFT_WINDOW_MINUTES` | `60` | Rolling reliability window used for drift detection. |
| `SAGE_PATTERN_DRIFT_MIN_SAMPLES` | `20` | Minimum observations before a drift window can demote an active pattern. |
| `SAGE_PATTERN_DRIFT_MAX_DROP` | `0.05` | Maximum tolerated reliability drop before cooling an active pattern. |

## Embeddings

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_EMBEDDING_PROVIDER` | `hash` | Embedding backend. Deterministic hash mode is local/offline. |
| `SAGE_EMBEDDING_API_URL` | empty | External compatible embedding endpoint. Production external learned embedding URLs require HTTPS. |
| `SAGE_EMBEDDING_API_KEY` | empty | Credential for external embedding endpoint. |
| `SAGE_EMBEDDING_MODEL` | empty | Provider model identifier. |
| `SAGE_EMBEDDING_TIMEOUT_SECONDS` | `10` | External embedding timeout. |

## References, cache, bus, and retention

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_REF_ENCRYPTION_KEY` | empty | URL-safe base64 AES-GCM key decoding to exactly 32 bytes. |
| `SAGE_REQUIRE_REF_ENCRYPTION` | `false` | Rejects unencrypted reference storage when enabled. |
| `SAGE_DEFAULT_REF_TTL_SECONDS` | unset | Default reference-grant TTL. |
| `SAGE_SEMANTIC_CACHE_ENABLED` | `true` | Enables semantic packet cache. |
| `SAGE_SEMANTIC_CACHE_TTL_SECONDS` | `3600` | Cache lifetime. |
| `SAGE_BUS_CLAIM_LEASE_SECONDS` | `60` | Claim lease before unacknowledged messages can be reclaimed. |
| `SAGE_DEFAULT_BUS_TTL_SECONDS` | unset | Default bus message TTL. |
| `SAGE_AUDIT_RETENTION_DAYS` | `30` | Audit retention window. |
| `SAGE_STATE_RETENTION_DAYS` | `90` | Minimum age before unreachable immutable states may be collected. |
| `SAGE_CHECKPOINT_INTERVAL_REVISIONS` | `1000` | Immutable-state revision interval for automatic content-addressed checkpoints. |
| `SAGE_IDEMPOTENCY_TTL_SECONDS` | `86400` | Server-side idempotency record lifetime. |
| `SAGE_QUOTA_WINDOW_SECONDS` | `60` | Rolling quota counter window. |
| `SAGE_QUOTA_HANDOFFS_PER_WINDOW` | `10000` | Workspace handoff allowance per quota window. |
| `SAGE_QUOTA_HANDOFFS_PER_AGENT_WINDOW` | `2000` | Per-agent handoff allowance within a workspace per quota window. |
| `SAGE_QUOTA_REF_BYTES_PER_WINDOW` | `1000000000` | Workspace reference-write byte allowance per quota window. |
| `SAGE_QUOTA_PATTERN_OBSERVATIONS_PER_WINDOW` | `100000` | Workspace pattern-observation allowance per quota window. |
| `SAGE_MAX_PENDING_MESSAGES_PER_WORKSPACE` | `100000` | Pending/claimed queue ceiling used for backpressure. |
| `SAGE_BACKPRESSURE_DEGRADED_RATIO` | `0.70` | Queue ratio that reports degraded state. |
| `SAGE_BACKPRESSURE_THROTTLED_RATIO` | `0.90` | Queue ratio that rejects new handoffs with throttling. |
| `SAGE_BUS_PARTITION_COUNT` | `64` | Deterministic logical partition count for durable handoffs. |
| `SAGE_GC_RETAIN_AUDIT_REPLAY` | `true` | Retains reference roots needed by audit/replay during reachability cleanup. |

## Signatures and federation

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_PACKET_SIGNING_PRIVATE_KEY` | empty | URL-safe base64 raw Ed25519 private key. |
| `SAGE_PACKET_SIGNING_PUBLIC_KEY` | empty | URL-safe base64 raw Ed25519 public key. |
| `SAGE_PACKET_SIGNING_KEY_ID` | `default` | Key identifier written into signatures. |
| `SAGE_REQUIRE_PACKET_SIGNATURES` | `false` | Requires valid packet signatures. Startup requires a public verification key when enabled. |
| `SAGE_FEDERATION_TIMEOUT_SECONDS` | `10` | Federation network timeout. |

## Benchmarks and observability

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_NATIVE_TOKEN_MIN_EVAL_SCORE` | `0.98` | Minimum evaluation score before native semantic-token use is allowed. |
| `SAGE_BENCHMARK_TOKENIZER_API_KEY` | empty | Server-side credential for external tokenizer service. |
| `SAGE_BENCHMARK_TOKENIZER_ALLOWED_HOSTS` | empty | Comma-separated tokenizer host allowlist. |
| `SAGE_OTEL_ENABLED` | `false` | Enables OpenTelemetry instrumentation when optional packages are installed. |
| `SAGE_OTEL_SERVICE_NAME` | `sage` | OpenTelemetry service name. |

## Routing

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_ROUTING_COST_WEIGHT` | `1.0` | Cost term in semantic route selection. |
| `SAGE_ROUTING_LATENCY_WEIGHT` | `0.001` | Latency term in semantic route selection. |
| `SAGE_ROUTING_KNOWLEDGE_WEIGHT` | `2.0` | Receiver-knowledge term in semantic route selection. |

Production configuration should be version-controlled as deployment metadata without embedding secret values. Runtime secret values should come from a secret manager or equivalent protected mechanism.
