from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.2.1"
EXPECTED_RELEASE = "v0.2"
EXPECTED_PROTOCOL = "sage/0.2"
EXPECTED_WIRE = 2
EXPECTED_REPOSITORY = "https://github.com/NeuralBinary/SAGE"
EXPECTED_AUTHOR = "NeuralBinary"
EXPECTED_CREDITS = ["@NeuralBinary", "@ro0ti"]


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"release consistency check failed: {message}")


def text_files(root: Path):
    paths = [root] if root.is_file() else root.rglob("*")
    for path in paths:
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix in {".pyc", ".tgz", ".whl", ".zip", ".db"}:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def main() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    require(project["version"] == EXPECTED_VERSION, "pyproject version drift")
    require(project["authors"] == [{"name": EXPECTED_AUTHOR}], "pyproject author drift")
    require([item["name"] for item in project["maintainers"]] == ["NeuralBinary", "ro0ti"], "pyproject maintainers drift")
    require(project["urls"]["Repository"] == EXPECTED_REPOSITORY, "pyproject repository drift")

    plugin = load_json("plugin.json")
    require(plugin["name"] == "SAGE", "plugin project name drift")
    require(plugin["version"] == EXPECTED_VERSION, "plugin version drift")
    require(plugin["release"] == EXPECTED_RELEASE, "plugin public release drift")
    require(plugin["protocol"] == EXPECTED_PROTOCOL, "plugin protocol drift")
    require(plugin["author"] == EXPECTED_AUTHOR, "plugin author drift")
    require(plugin["credits"] == EXPECTED_CREDITS, "plugin credits drift")
    require(plugin["repository"] == EXPECTED_REPOSITORY, "plugin repository drift")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for value in ["Project | SAGE", "Author | NeuralBinary", EXPECTED_REPOSITORY, "@NeuralBinary, @ro0ti", f"Version | {EXPECTED_RELEASE}"]:
        require(value in readme, f"README metadata missing: {value}")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    require("Copyright (c) 2026 NeuralBinary" in license_text, "license attribution drift")

    openclaw_pkg = load_json("integrations/openclaw/package.json")
    openclaw_manifest = load_json("integrations/openclaw/openclaw.plugin.json")
    require(openclaw_pkg["version"] == EXPECTED_VERSION, "OpenClaw package version drift")
    require(openclaw_pkg["author"] == EXPECTED_AUTHOR, "OpenClaw author drift")
    require(openclaw_pkg["contributors"] == ["NeuralBinary", "ro0ti"], "OpenClaw credits drift")
    require(openclaw_pkg["repository"]["url"] == f"git+{EXPECTED_REPOSITORY}.git", "OpenClaw repository drift")
    require(openclaw_manifest["version"] == EXPECTED_VERSION, "OpenClaw manifest version drift")

    hermes_yaml = (ROOT / "integrations/hermes/sage/plugin.yaml").read_text(encoding="utf-8")
    require(re.search(r'^version:\s*["\']?0\.2\.1["\']?\s*$', hermes_yaml, re.MULTILINE) is not None, "Hermes manifest version drift")

    init_py = (ROOT / "src/sage_plugin/__init__.py").read_text(encoding="utf-8")
    protocol_py = (ROOT / "src/sage_plugin/protocol_spec.py").read_text(encoding="utf-8")
    require(f'__version__ = "{EXPECTED_VERSION}"' in init_py, "Python package version drift")
    require(f'SAGE_PROTOCOL = "{EXPECTED_PROTOCOL}"' in protocol_py, "protocol constant drift")
    require(f"SAGE_WIRE_VERSION = {EXPECTED_WIRE}" in protocol_py, "wire constant drift")

    tck = load_json("tck/vectors/core.json")
    require(tck["protocol"] == EXPECTED_PROTOCOL, "TCK protocol drift")
    require(tck["wire_version"] == EXPECTED_WIRE, "TCK wire version drift")
    require(load_json("src/sage_plugin/tck/vectors/core.json") == tck, "packaged TCK differs from repository TCK")
    implementations = load_json("tck/implementations.json")
    require(implementations["suite"] == "sage-tck/0.2", "TCK implementation matrix drift")
    require(load_json("src/sage_plugin/tck/implementations.json") == implementations, "packaged TCK implementation matrix drift")
    require({item["id"] for item in implementations["implementations"]} == {"python", "javascript", "go"}, "TCK implementation matrix incomplete")

    required = [
        "scripts/conformance_matrix.py",
        "scripts/differential_fuzz.py",
        "scripts/architecture_check.py",
        "scripts/cluster_chaos.py",
        "scripts/soak_cluster.py",
        "scripts/model_matrix_benchmark.py",
        "scripts/invariant_check.py",
        "scripts/generate_protocol_artifacts.py",
        "scripts/generate_specs.py",
        "scripts/package_check.py",
        "integrations/go/conformance.go",
        "integrations/openclaw/dist/index.js",
        "integrations/openclaw/dist/conformance.js",
        "integrations/openclaw/tck/core.json",
        "integrations/openclaw/package.json",
        "integrations/openclaw/openclaw.plugin.json",
        "deploy/staging/compose.yml",
        ".github/workflows/scale.yml",
        "deploy/staging/nginx.conf",
        "src/sage_plugin/corpus.py",
        "src/sage_plugin/api_transport.py",
        "src/sage_plugin/api_memory.py",
        "src/sage_plugin/api_learning.py",
        "src/sage_plugin/api_semantic.py",
        "src/sage_plugin/api_helpers.py",
        "src/sage_plugin/pattern_structure.py",
        "src/sage_plugin/telemetry.py",
        "src/sage_plugin/information_flow.py",
        "src/sage_plugin/reachability.py",
        "src/sage_plugin/qualification.py",
        "src/sage_plugin/inspector_ui.py",
        "src/sage_plugin/pattern_policy.py",
        "src/sage_plugin/reliability.py",
        "src/sage_plugin/merkle.py",
        "src/sage_plugin/codebook_releases.py",
        "spec/invariants.json",
        "spec/generated/manifest.json",
        "docs/THREAT_MODEL.md",
        "docs/ARCHITECTURE.md",
        "docs/INVARIANTS.md",
        "spec/SAGE-0.2.md",
        "spec/sage-v0.2.proto",
        "spec/schemas/wire-v2.schema.json",
        "spec/schemas/pattern-v0.2.schema.json",
        "src/sage_plugin/spec/SAGE-0.2.md",
        "src/sage_plugin/spec/sage-v0.2.proto",
        "src/sage_plugin/spec/schemas/wire-v2.schema.json",
        "src/sage_plugin/spec/schemas/pattern-v0.2.schema.json",
    ]
    for rel in required:
        require((ROOT / rel).is_file(), f"missing required v0.2 artifact: {rel}")

    require((ROOT / "spec/SAGE-0.2.md").read_bytes() == (ROOT / "src/sage_plugin/spec/SAGE-0.2.md").read_bytes(), "packaged protocol specification drift")
    require((ROOT / "spec/sage-v0.2.proto").read_bytes() == (ROOT / "src/sage_plugin/spec/sage-v0.2.proto").read_bytes(), "packaged protobuf binding drift")

    repo_schemas = sorted((ROOT / "spec/schemas").glob("*.json"))
    require(repo_schemas, "no normative schemas found")
    for schema_path in repo_schemas:
        packaged = ROOT / "src/sage_plugin/spec/schemas" / schema_path.name
        require(packaged.is_file(), f"missing packaged schema: {schema_path.name}")
        require(schema_path.read_bytes() == packaged.read_bytes(), f"packaged schema drift: {schema_path.name}")

    wire_schema = load_json("spec/schemas/wire-v2.schema.json")
    require("g" in wire_schema.get("properties", {}), "wire signature field missing from schema")
    require("z" in wire_schema.get("properties", {}), "wire trace field missing from schema")
    require("e" in wire_schema.get("$defs", {}).get("WireAtomV2", {}).get("properties", {}), "wire epistemic field missing from schema")
    require("signature" in load_json("spec/schemas/packet-v0.2.schema.json").get("properties", {}), "readable packet signature missing from schema")


    generated = load_json("spec/generated/manifest.json")
    require(generated["protocol"] == EXPECTED_PROTOCOL, "generated protocol manifest drift")
    require(generated["wire"] == EXPECTED_WIRE, "generated wire manifest drift")
    require(set(generated.get("artifacts", {})) >= {
        "spec/generated/wire-v2.ts",
        "spec/generated/wire-v2.go",
        "spec/generated/WIRE-FIELDS.md",
        "spec/sage-v0.2.proto",
        "src/sage_plugin/spec/sage-v0.2.proto",
    }, "generated protocol artifact manifest incomplete")

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    require("alembic upgrade head &&" not in dockerfile, "application container must not race schema migrations")
    root_compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    staging_compose = (ROOT / "deploy/staging/compose.yml").read_text(encoding="utf-8")
    require('command: ["alembic", "upgrade", "head"]' in root_compose, "root Compose migration service missing")
    require('command: ["alembic", "upgrade", "head"]' in staging_compose, "staging migration service missing")

    migration_files = sorted(path.name for path in (ROOT / "alembic/versions").glob("*.py") if path.name != "__init__.py")
    require(migration_files == ["0001_sage_0_2_baseline.py"], f"unexpected migration history: {migration_files}")

    obsolete_patterns = [
        re.compile(r"sage/0\.(?:1|[3-9])"),
        re.compile(r"\bv0\.(?:1|[3-9])(?:\.\d+)?\b"),
        re.compile(r"\b0\.(?:1|[3-9])\.0\b"),
        re.compile(r"wire-v(?:1|[3-9])"),
        re.compile(r"SAGE-0\.(?:1|[3-9])"),
        re.compile(r"sage-v0\.(?:1|[3-9])"),
    ]
    prose_forbidden = re.compile(r"\b(?:example|examples|placeholder|placeholders|mock|mocks|scaffold|scaffolding|guess|guessing)\b", re.IGNORECASE)
    obsolete: list[str] = []
    prose_violations: list[str] = []
    for scan_root in [ROOT / "src", ROOT / "spec", ROOT / "tck", ROOT / "docs", ROOT / "integrations", ROOT / "README.md", ROOT / "VERIFICATION.md", ROOT / "plugin.json", ROOT / "pyproject.toml"]:
        for path, text in text_files(scan_root):
            rel = str(path.relative_to(ROOT))
            if any(pattern.search(text) for pattern in obsolete_patterns):
                obsolete.append(rel)
            if path.suffix in {".md", ".txt"} and prose_forbidden.search(text):
                prose_violations.append(rel)
    require(not obsolete, f"obsolete version markers: {sorted(set(obsolete))}")
    require(not prose_violations, f"development prose found: {sorted(set(prose_violations))}")

    forbidden_artifacts: list[str] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if rel.parts and rel.parts[0] in {"build", "dist"}:
            forbidden_artifacts.append(str(rel))
            continue
        if any(part in {".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__"} for part in rel.parts):
            forbidden_artifacts.append(str(rel))
            continue
        if path.is_file() and (path.suffix in {".pyc", ".db", ".sqlite", ".sqlite3"} or path.name.endswith(".egg-info")):
            forbidden_artifacts.append(str(rel))
        if path.is_dir() and path.name.endswith(".egg-info"):
            forbidden_artifacts.append(str(rel))
        if path.is_file() and path.suffix == ".tgz" and "integrations/openclaw" in str(rel):
            forbidden_artifacts.append(str(rel))
    require(not forbidden_artifacts, f"generated/runtime artifacts in source tree: {sorted(set(forbidden_artifacts))[:20]}")

    print(json.dumps({
        "ok": True,
        "project": "SAGE",
        "author": EXPECTED_AUTHOR,
        "release": EXPECTED_RELEASE,
        "version": EXPECTED_VERSION,
        "protocol": EXPECTED_PROTOCOL,
        "wire": EXPECTED_WIRE,
        "migration": migration_files[0],
        "tck_vectors": len(tck.get("valid", [])) + len(tck.get("invalid", [])),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
