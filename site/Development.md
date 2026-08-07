
# Development

## Repository layout

```text
src/sage_plugin/          core runtime and Python adapters
spec/                     frozen protocol, schemas, protobuf binding
tck/                      language-neutral conformance vectors (13)
tests/                    behavioral and protocol tests
integrations/             host-specific adapters (hermes, openclaw, go, a2a, claude)
docs/                     operations, security, patterns, configuration
alembic/                  single v0.2 database baseline (0001_sage_0_2)
scripts/                  release, performance, schema, and verification tools
```

## Install an editable dev environment

Python 3.11 or newer is required:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Optional dependency groups: `postgres` (psycopg), `mcp` (MCP SDK), `bench` (tiktoken), `otel` (OpenTelemetry).

## Core test and check commands

```bash
pytest -q                      # full behavioral + protocol suite
ruff check src tests scripts   # lint
python scripts/security_check.py
python scripts/architecture_check.py
python scripts/invariant_check.py
python scripts/generate_specs.py --check            # (with PYTHONPATH=src)
python scripts/generate_protocol_artifacts.py --check
sage-tck --json
python scripts/conformance_matrix.py                # Python + JS + Go
python scripts/differential_fuzz.py --iterations 250
python scripts/chaos_suite.py
python scripts/performance_check.py --iterations 200
sage-qualify --profile-encode --profile-iterations 30 --max-query-count 40
python scripts/release_check.py
```

`make verify` runs the full local sequence: security, architecture, invariants, generated schema/artifact checks, TCK, the three-runtime conformance matrix, differential fuzzing, chaos recovery, the full test suite, latency and query-budget gates, byte compilation, cleanup, and the final source-tree release consistency check.

## TCK and cross-runtime conformance

- `sage-tck --json` runs the 13 normative vectors (6 valid + 7 invalid) against the installed package.
- `python scripts/conformance_matrix.py` executes all required runtimes from `tck/implementations.json` — Python, JavaScript (`node integrations/openclaw/dist/conformance.js`), and Go (`go run integrations/go/conformance.go`) — each of which must pass 13/13.
- `python scripts/differential_fuzz.py --iterations N` compares canonical MessagePack identity and validation behavior across independent runtimes.
- `python scripts/generate_protocol_artifacts.py --check` and `generate_specs.py --check` detect drift between generated schemas/protobuf/TCK artifacts and the repository/package copies.

## release_check.py artifact requirements

`python scripts/release_check.py` enforces package metadata, author/credit metadata, protocol/wire identity, one baseline migration, schema parity, TCK parity, repository hygiene, and v0.2 consistency.

It also enforces the **presence of the OpenClaw build outputs**. Before running it, build the OpenClaw adapter and remove the build caches, exactly as CI does:

```bash
cd integrations/openclaw
npm install --ignore-scripts
npm run build
cd ../..
rm -rf integrations/openclaw/node_modules integrations/openclaw/package-lock.json
python scripts/release_check.py
```

The OpenClaw `dist/` outputs (`dist/index.js`, `dist/conformance.js`) cannot be produced without this build step; `release_check.py` fails when either output is absent or stale.

## Building a release

```bash
python scripts/build_release.py --output dist
python scripts/package_check.py \
  --source dist/sage-plugin-v0.2.7.zip \
  --wheel dist/sage_agent_protocol-0.2.7-py3-none-any.whl \
  --hermes dist/sage-hermes-plugin-v0.2.7.zip \
  --openclaw dist/sage-agent-openclaw-sage-0.2.7.tgz
```

`scripts/package_check.py` verifies package metadata, author, the Hermes entry point, protocol specification, protobuf binding, nested JSON Schemas, TCK implementation matrix, and TCK vectors directly from the wheel archive, plus the OpenClaw package (`--openclaw`). For reproducible builds, the release workflow pins `SOURCE_DATE_EPOCH`.

Release assets:

```text
Python/runtime   -> sage_agent_protocol-0.2.7-py3-none-any.whl
Hermes Agent     -> sage-hermes-plugin-v0.2.7.zip
OpenClaw         -> sage-agent-openclaw-sage-0.2.7.tgz
Source           -> sage-plugin-v0.2.7.zip
Verification     -> SAGE-v0.2.7-VERIFICATION.md
Checksums        -> SAGE-v0.2.7-SHA256SUMS.txt
```

## Release workflow

Version identity is locked across `pyproject.toml`, `plugin.json`, the Python package, the Hermes manifest and adapter, the OpenClaw package and manifest, the spec, the TCK, and current-release documentation. Release commits prepare that identity (e.g. `release: prepare v0.2.7`).

Pushing a tag matching `v*` triggers `.github/workflows/release.yml`, which:

1. builds and qualifies the OpenClaw adapter (npm install `--ignore-scripts`, `npm run check`, `npm run build`, `npm run tck`);
2. installs and qualifies the Python source (`pytest`, `release_check.py`, generated spec and protocol artifact checks);
3. builds every release asset with `scripts/build_release.py --output dist`;
4. verifies packaged assets with `scripts/package_check.py` and `node scripts/openclaw_adapter_check.mjs`;
5. tests the installed wheel in a fresh virtual environment (`sage-doctor --help`, `sage-demo --help`);
6. runs the Docker quick-start gate (`docker compose -f docker-compose.quickstart.yml up --build -d --wait`, `sage-doctor`, `sage-demo --single-agent`);
7. publishes the GitHub release with the asset set and computes SHA-256 checksums.

## CI overview (.github/workflows/ci.yml)

The `ci` workflow runs on push and pull request:

- **python** — Python 3.11–3.14 matrix with Go 1.24 and Node 24.15.0: ruff, strict mypy over the entire Python package, security/architecture/invariant checks, generated spec/protocol artifact checks, `sage-tck --json`, conformance matrix, differential fuzzing (250 iterations), chaos suite, byte compilation, full pytest with at least 80% source coverage, performance gate (200 iterations), encode query-budget profile, cache cleanup, `release_check.py` (after `rm -rf integrations/openclaw/node_modules ...`), and migration verification (`alembic upgrade head` + `alembic check` on SQLite).
- **postgres** — Python 3.14 against PostgreSQL 18: `alembic upgrade head`/`check`, full suite with `SAGE_TEST_USE_CONFIGURED_DB=true`, configured-database concurrency (`--configured-concurrency --workers 8 --messages 20`), and configured-database ordering (`--configured-ordering`).
- **dependency-audit** — installs `.[postgres,mcp,bench,otel]` and runs `pip-audit --local`.
- **openclaw-adapter** — Node 24.15.0: `npm install --ignore-scripts`, `npm run check`, `npm run build`, `npm run tck`, `node --check dist/index.js`, `node scripts/openclaw_adapter_check.mjs`, `npm pack --ignore-scripts`, then `scripts/package_check.py --openclaw`.
- **package** — builds and verifies all release assets (`build_release.py --output dist --skip-openclaw`, `package_check.py` for source/wheel/hermes), MCP construction check (`build_server()`), and `docker build -t sage-agent-protocol:test .`.
- **staging-cluster** — generates a one-day self-signed TLS certificate with `openssl`, configures `SAGE_POSTGRES_PASSWORD`/`SAGE_API_KEYS`/`SAGE_ALLOWED_HOSTS`/`SAGE_TLS_CERT`/`SAGE_TLS_KEY`, validates and starts `deploy/staging/compose.yml` (`--wait`), runs `scripts/soak_cluster.py` (10 s, 8 workers, rate 8) against `https://localhost:8443`, runs `scripts/cluster_chaos.py --disrupt-postgres`, then collects logs and tears down.

A dispatch-only `.github/workflows/scale.yml` accepts vocabulary-size and soak-duration inputs for sustained release-candidate qualification (default vocabulary 1,000,000 concepts; default soak 24 hours).

## Qualification numbers (v0.2.6 verification record)

- 236 tests pass on the release tree with the `[dev,mcp,bench,otel]` extras installed.
- 13/13 TCK vectors in Python, JavaScript, and Go; 250/250 malformed-wire mutations; 1,000 cross-runtime differential comparisons.
- 21 release invariants, each mapped to an executable qualification target (`scripts/invariant_check.py` passes).
- OpenAPI builds as 3.1.0 with 81 paths.
- Local latency gates (200 iterations, SQLite): core encode p95 ≤ 40 ms, core decode p95 ≤ 10 ms, HTTP send p95 ≤ 75 ms, HTTP receive p95 ≤ 50 ms; encode query profile ≤ 40 SQL statements.

Next: [Production](Production.md)
