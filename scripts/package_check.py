from __future__ import annotations

import argparse
import json
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

VERSION = "0.2.1"
AUTHOR = "NeuralBinary"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"package check failed: {message}")


def check_wheel(path: Path) -> dict[str, object]:
    require(path.is_file(), f"wheel missing: {path}")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_name = next((name for name in names if name.endswith(".dist-info/METADATA")), None)
        entry_name = next((name for name in names if name.endswith(".dist-info/entry_points.txt")), None)
        require(metadata_name is not None, "wheel METADATA missing")
        require(entry_name is not None, "wheel entry points missing")
        metadata = Parser().parsestr(archive.read(metadata_name).decode())
        require(metadata.get("Version") == VERSION, "wheel version drift")
        require(metadata.get("Author") == AUTHOR, "wheel author drift")
        required = {
            "sage_plugin/spec/SAGE-0.2.md",
            "sage_plugin/spec/sage-v0.2.proto",
            "sage_plugin/spec/schemas/wire-v2.schema.json",
            "sage_plugin/spec/schemas/pattern-v0.2.schema.json",
            "sage_plugin/tck/implementations.json",
            "sage_plugin/tck/vectors/core.json",
        }
        missing = sorted(required - names)
        require(not missing, f"wheel protocol content missing: {missing}")
        entries = archive.read(entry_name).decode()
        require("[hermes_agent.plugins]" in entries and "sage = sage_plugin.hermes_plugin" in entries, "Hermes entry point missing")
    return {"wheel": path.name, "entries": len(names), "ok": True}


def check_openclaw(path: Path) -> dict[str, object]:
    require(path.is_file(), f"OpenClaw package missing: {path}")
    with tarfile.open(path, "r:gz") as archive:
        names = set(archive.getnames())
        required = {
            "package/package.json",
            "package/openclaw.plugin.json",
            "package/dist/index.js",
            "package/dist/conformance.js",
            "package/tck/core.json",
        }
        missing = sorted(required - names)
        require(not missing, f"OpenClaw content missing: {missing}")
        package_member = archive.extractfile("package/package.json")
        require(package_member is not None, "OpenClaw package metadata unreadable")
        package = json.loads(package_member.read())
        require(package.get("version") == VERSION, "OpenClaw version drift")
        require(package.get("author") == AUTHOR, "OpenClaw author drift")
        require(package.get("contributors") == ["NeuralBinary", "ro0ti"], "OpenClaw credits drift")
    return {"openclaw": path.name, "entries": len(names), "ok": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--openclaw", type=Path)
    args = parser.parse_args()
    require(args.wheel is not None or args.openclaw is not None, "at least one package path is required")
    result: dict[str, object] = {"ok": True}
    if args.wheel is not None:
        result["python"] = check_wheel(args.wheel)
    if args.openclaw is not None:
        result["openclaw"] = check_openclaw(args.openclaw)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
