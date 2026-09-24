from __future__ import annotations
import os
from pathlib import Path

MAX_CANDIDATES = [
    rf"C:\Program Files\Autodesk\3ds Max {year}\3dsmax.exe"
    for year in range(2020, 2027)
]


def first_existing(candidates: list[str]) -> str:
    for item in candidates:
        if item and Path(item).is_file():
            return str(Path(item).resolve())
    return ""


def detect_max() -> str:
    env = os.environ.get("COMPASS_3DSMAX_EXE", "")
    detected = first_existing([env, *MAX_CANDIDATES])
    if not detected:
        return ""
    batch = Path(detected).with_name("3dsmaxbatch.exe")
    return detected if batch.is_file() else ""


def detect_blender(root: Path) -> str:
    env = os.environ.get("COMPASS_BLENDER_EXE", "")
    candidates = [
        env,
        str(root / "runtime" / "blender" / "blender.exe"),
        str(root / "runtime" / "blender" / "blender-launcher.exe"),
    ]
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    blender_root = program_files / "Blender Foundation"
    if blender_root.is_dir():
        candidates.extend(str(p) for p in sorted(blender_root.glob("Blender */blender.exe"), reverse=True))
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    if local:
        candidates.extend(str(p) for p in sorted(local.glob("Programs/Blender Foundation/Blender */blender.exe"), reverse=True))
    return first_existing(candidates)
