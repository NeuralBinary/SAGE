# Contributing to SAGE

Thank you for helping improve SAGE. Contributions should preserve its core promise:
semantic compression must remain recoverable, secure, deterministic where specified, and
interoperable across the Python, JavaScript, and Go protocol implementations.

## Before opening a change

- Use a GitHub issue for substantial behavior, protocol, storage, or security changes so the
  design can be discussed before implementation.
- Keep protocol `sage/0.2`, wire version `2`, generated schemas, and TCK vectors synchronized.
- Do not include credentials, private evaluation data, generated build output, caches, or local
  databases.
- Report suspected vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Development setup

SAGE supports Python 3.11 through 3.14. Create an isolated environment and install the
development dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev,mcp]'
```

On Windows, activate with `.venv\Scripts\activate`.

Run the fast local gates while developing:

```bash
ruff check src tests scripts
mypy src/sage_plugin
pytest -q
```

Before requesting review, run `make verify` on a Unix-like environment when practical. It adds
the security, architecture, invariant, generated-artifact, conformance, fuzz, chaos,
performance, query-budget, and release-consistency checks used by CI.

The OpenClaw adapter requires its declared Node version and is checked separately:

```bash
cd integrations/openclaw
npm install --ignore-scripts
npm run check
npm run build
npm run tck
```

## Tests and compatibility

- Add a regression test for every bug fix and behavioral test coverage for new public APIs.
- Do not weaken semantic-fidelity, security, coverage, performance, or query-budget gates to
  make a change pass.
- Generated protocol files must be regenerated with the repository scripts, never edited in
  isolation.
- Database changes require an Alembic migration and successful `alembic check` on SQLite and
  PostgreSQL.
- Public behavior and operator-facing configuration changes require matching documentation.

## Pull requests

Keep pull requests focused. Explain the problem, the chosen behavior, compatibility or security
impact, and the verification performed. Reviewers may ask for additional cross-runtime TCK,
failure-mode, concurrency, or migration evidence when the affected boundary warrants it.

## Contributor license agreement

SAGE uses dual licensing, so accepted third-party contributions need an explicit inbound grant that permits both the open-source and commercial distributions. Before submitting a pull request, read [CONTRIBUTOR_LICENSE_AGREEMENT.md](CONTRIBUTOR_LICENSE_AGREEMENT.md).

By submitting a pull request and checking the CLA acknowledgement in the pull-request template, you agree to that CLA for the contribution. You retain copyright in your work. The CLA grants NeuralBinary the rights needed to distribute accepted contributions under `AGPL-3.0-or-later` and under separately negotiated commercial SAGE licenses.

If you are contributing on behalf of an employer or another legal entity, confirm that you have authority to make the contribution and grant those rights. NeuralBinary may request a separately signed agreement for material corporate contributions.

If you cannot agree to the CLA, open an issue before submitting code so the licensing question can be resolved first.

Participation also follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).