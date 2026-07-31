from __future__ import annotations

import json
from pathlib import Path

from sage_plugin.protocol_spec import WirePacketV1
from sage_plugin.spec_models import SPEC_MODELS

ROOT = Path(__file__).resolve().parents[1]


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    repo = ROOT / "spec" / "schemas"
    packaged = ROOT / "src" / "sage_plugin" / "spec"
    for name, model in SPEC_MODELS.items():
        payload = model.model_json_schema()
        filename = f"{name}-v0.1.schema.json"
        dump(repo / filename, payload)
        dump(packaged / filename, payload)
    wire = WirePacketV1.model_json_schema(by_alias=True)
    dump(repo / "wire-v1.schema.json", wire)
    dump(packaged / "wire-v1.schema.json", wire)


if __name__ == "__main__":
    main()
