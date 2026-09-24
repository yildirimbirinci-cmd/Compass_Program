from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class EngineConfig:
    max_exe: str
    blender_exe: str
    timeout_seconds: int = 1800
    keep_temp: bool = False
    export_hidden: bool = False
    include_cameras: bool = False
    include_lights: bool = False

    @classmethod
    def load(cls, path: Path) -> "EngineConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)
