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

By contributing, you agree that your contribution is licensed under the same dual-licensing
terms as the project:

1. **AGPL-3.0** — For open source use
2. **Commercial License** — For proprietary use (sold by NeuralBinary)

This allows SAGE to remain fully open source while providing a sustainable path for
continued development through commercial licensing. Your copyright is retained; you're
simply granting permission for your work to be distributed under both licenses.

If you have questions about this, please open an issue or contact us at
sage@neuralbinary.com before contributing.

Participation also follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).