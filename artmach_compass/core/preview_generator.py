from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import traceback
from typing import Any
import uuid
import zipfile

from PySide6.QtCore import QThread, Signal

from artmach_compass.conversion_engine.engine.config import EngineConfig
from artmach_compass.conversion_engine.engine.discovery import detect_blender, detect_max
from artmach_compass.conversion_engine.engine.pipeline import ConversionPipeline


class PreviewGenerationThread(QThread):
    """Run the external 3ds Max/Blender pipeline without blocking Compass UI."""

    stage_changed = Signal(str, int)
    succeeded = Signal(str, dict)
    failed = Signal(str, str)

    def __init__(self, source_max: str, parent=None) -> None:
        super().__init__(parent)
        self.source_max = Path(source_max)

    @staticmethod
    def engine_root() -> Path:
        return Path(__file__).resolve().parents[1] / "conversion_engine"

    @staticmethod
    def runtime_root() -> Path:
        local_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local_root / "ArtmachCompass" / "PreviewEngine"

    def _write_emergency_diagnostics(self, error: BaseException, *, stage: str) -> str:
        """Create a support ZIP even when failure happens before ConversionPipeline starts."""
        runtime_root = self.runtime_root()
        logs_root = runtime_root / "logs"
        logs_root.mkdir(parents=True, exist_ok=True)
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        json_path = logs_root / f"{job_id}_preview_emergency.json"
        bundle_path = logs_root / f"{job_id}_diagnostics.zip"
        payload = {
            "job_id": job_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "source_max": str(self.source_max),
            "engine_root": str(self.engine_root()),
            "runtime_root": str(runtime_root),
            "localappdata": os.environ.get("LOCALAPPDATA", ""),
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(json_path, arcname=json_path.name)
        shutil.copy2(bundle_path, logs_root / "Latest_Diagnostics.zip")
        (logs_root / "Latest_Diagnostics.txt").write_text(str(bundle_path), encoding="utf-8")
        return str(bundle_path)

    def run(self) -> None:
        diagnostics_path = ""
        stage = "initializing preview generation"
        try:
            root = self.engine_root()
            stage = "detecting 3ds Max and Blender"
            self.stage_changed.emit("Checking 3ds Max and Blender...", 8)
            config_path = root / "config" / "engine.json"
            config = EngineConfig.load(config_path)
            detected_max = detect_max()
            detected_blender = detect_blender(root)
            config = replace(
                config,
                max_exe=config.max_exe if config.max_exe and Path(config.max_exe).is_file() else detected_max,
                blender_exe=(
                    config.blender_exe
                    if config.blender_exe and Path(config.blender_exe).is_file()
                    else detected_blender
                ),
            )
            if not config.max_exe:
                raise RuntimeError("3ds Max was not detected.")
            if not config.blender_exe:
                raise RuntimeError(
                    "Blender was not detected. Run the bundled setup_engine.cmd once."
                )

            output = self.source_max.with_name(self.source_max.stem + "_preview.glb")
            self.stage_changed.emit("Analyzing scene and exporting FBX...", 24)
            stage = "starting conversion pipeline"
            runtime_root = self.runtime_root()
            runtime_root.mkdir(parents=True, exist_ok=True)
            report = ConversionPipeline(root, config, runtime_root=runtime_root).convert(
                self.source_max, output
            )
            self.stage_changed.emit("Validating GLB preview...", 92)
            self.succeeded.emit(str(output), asdict(report))
        except Exception as exc:
            message = str(exc)
            marker = "Diagnostic package: "
            if marker in message:
                diagnostics_path = message.split(marker, 1)[1].strip()
            if not diagnostics_path or not Path(diagnostics_path).is_file():
                try:
                    diagnostics_path = self._write_emergency_diagnostics(exc, stage=stage)
                    message = f"{message} Diagnostic package: {diagnostics_path}"
                except Exception as diagnostics_error:
                    message = f"{message} Diagnostics creation also failed: {diagnostics_error}"
            self.failed.emit(message, diagnostics_path)
