# SAGE Issue #1 Candidate Revision Report

- Baseline: `ef9768653cba98cb2871d41505bee82b36a2dfdc`
- Prior candidate: `0e836f1816c997d49669a949276a87b9954941d3`
- Revised commit: `2b7299acb5808ec353ac4377a6ae5cdac2ab4826`
- Repository: `/opt/data/sage/candidates/sage-issue-1`
- Branch: `sage/issue-1`

## Changes

- Added a subprocess regression test that changes into `/proc`, sets an isolated writable `HOME`, imports the real database module, runs `init_db()`, verifies the `concepts` table, and proves `HOME/sage.db` is created. This avoids root-only chmod assumptions and exercises the database initialization seam.
- Updated `docs/CONFIGURATION.md` to document the home-directory default and explicit `SAGE_DATABASE_URL` precedence.
- Removed the contradictory cwd-relative Alembic URL from `alembic.ini`; `alembic/env.py` remains the single source of runtime settings and therefore preserves explicit overrides and the home-directory default.
- Production SQLite rejection and explicit URL tests remain unchanged and passing.

## Verification

- Focused config tests: `uv run --with '.[dev]' pytest tests/test_config.py -q` — **4 passed**.
- Full suite: `uv run --with '.[dev]' pytest -q` — **108 passed**; one pre-existing Starlette/httpx deprecation warning.
- Diff check: `git diff --check` — **passed**.
- Ruff: `uv run --with '.[dev]' ruff check src tests` — **not clean due to 96 pre-existing repository findings**, unrelated to this change; no candidate files were auto-fixed.
- Wheel build: `uv build --wheel` — **passed**.
- Wheel: `/opt/data/sage/candidates/sage-issue-1/dist/sage_agent_protocol-0.2.1-py3-none-any.whl`
- Wheel SHA-256: `2ff6c72d14e8fa9f331ecbbfa08485cb7253318c4b058d45eaf05842d429abe4`
- Fresh-wheel smoke test: installed the wheel into a temporary virtual environment and initialized the database from `/proc`; verified the home-directory SQLite URL and database usability.
- Explicit-path Alembic smoke test was attempted; the command succeeded in resolving the candidate, but the first invocation used `uv --with` from `/proc` and failed because `/proc` is not a project. The fresh-wheel runtime smoke test and full test suite passed. A direct explicit Alembic run was not counted as passing evidence.

## Scope and restrictions

Modified files: `tests/test_config.py`, `docs/CONFIGURATION.md`, `alembic.ini`, and this report. No credentials, tokens, Hermes control home, Kanban database, protected governance files, unrelated repositories, push, PR, merge, release, or activation operations were performed.

The worktree was clean after commit.
