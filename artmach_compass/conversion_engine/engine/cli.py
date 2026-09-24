from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

from .config import EngineConfig
from .discovery import detect_blender, detect_max
from .pipeline import ConversionPipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Compass MAX to GLB conversion engine")
    p.add_argument("source", nargs="?", help="Source .max file")
    p.add_argument("--output", help="Output .glb path")
    p.add_argument("--config", default="config/engine.json")
    p.add_argument("--detect", action="store_true", help="Print detected executables")
    p.add_argument("--dry-run", action="store_true", help="Validate configuration without conversion")
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[1]
    detected_max = detect_max()
    detected_blender = detect_blender(root)
    if args.detect:
        print(json.dumps({"3ds_max": detected_max, "blender": detected_blender}, indent=2))
        return 0
    config_path = (root / args.config).resolve()
    config = EngineConfig.load(config_path)
    config = replace(
        config,
        max_exe=config.max_exe if config.max_exe and Path(config.max_exe).is_file() else detected_max,
        blender_exe=config.blender_exe if config.blender_exe and Path(config.blender_exe).is_file() else detected_blender,
    )
    if args.dry_run:
        result = {
            "config": str(config_path),
            "max_exe": config.max_exe,
            "blender_exe": config.blender_exe,
            "max_exists": bool(config.max_exe) and Path(config.max_exe).is_file(),
            "blender_exists": bool(config.blender_exe) and Path(config.blender_exe).is_file(),
        }
        print(json.dumps(result, indent=2))
        return 0 if result["max_exists"] and result["blender_exists"] else 2
    if not args.source:
        raise SystemExit("source .max file is required")
    if not config.blender_exe:
        raise RuntimeError("Blender runtime is missing. Run setup_engine.cmd once, then retry.")
    if not config.max_exe:
        raise RuntimeError("3ds Max executable was not detected. Set max_exe in config\\engine.json.")
    source = Path(args.source)
    output = Path(args.output) if args.output else source.with_name(source.stem + "_preview.glb")
    report = ConversionPipeline(root, config).convert(source, output)
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
