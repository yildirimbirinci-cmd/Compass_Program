from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
import traceback
import uuid
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import EngineConfig
from .process import run_process
from .validator import validate_glb


@dataclass
class ConversionReport:
    source_max: str
    output_glb: str
    work_dir: str
    started_utc: str
    completed_utc: str = ""
    max_report: dict | None = None
    validation: dict | None = None
    status: str = "started"
    error: str = ""
    diagnostics_zip: str = ""


class ConversionPipeline:
    def __init__(self, root: Path, config: EngineConfig, runtime_root: Path | None = None):
        self.root = root.resolve()
        self.runtime_root = (runtime_root or root).resolve()
        self.config = config

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _numbered_source(path: Path) -> str:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(f"{index:05d}: {line}" for index, line in enumerate(lines, 1)) + "\n"

    def _create_diagnostics_bundle(
        self,
        *,
        job_id: str,
        logs_root: Path,
        work: Path,
        script_path: Path,
        input_json: Path,
        report_json: Path,
        texture_manifest: Path,
        fbx_path: Path,
        intermediate_glb: Path,
        source_max: Path,
        output_glb: Path,
        error: BaseException,
        max_cmd: list[str] | None,
    ) -> Path:
        diagnostics_root = self._diagnostics_root()
        bundle_path = diagnostics_root / f"{job_id}_diagnostics.zip"
        staging = work / "diagnostics"
        staging.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        candidates = [
            input_json,
            report_json,
            texture_manifest,
            fbx_path,
            intermediate_glb,
            logs_root / f"{job_id}_max_batch.log",
            logs_root / f"{job_id}_max_listener.log",
            logs_root / f"{job_id}_max_system.log",
            logs_root / f"{job_id}_blender.log",
        ]
        for candidate in candidates:
            if candidate.is_file():
                destination = staging / candidate.name
                shutil.copy2(candidate, destination)
                copied.append(destination.name)

        deployed_script = staging / "run_job_deployed.ms"
        shutil.copy2(script_path, deployed_script)
        copied.append(deployed_script.name)
        numbered_script = staging / "run_job_deployed_numbered.txt"
        numbered_script.write_text(self._numbered_source(script_path), encoding="utf-8")
        copied.append(numbered_script.name)

        config_snapshot = {
            "max_exe": self.config.max_exe,
            "blender_exe": self.config.blender_exe,
            "timeout_seconds": self.config.timeout_seconds,
            "keep_temp": self.config.keep_temp,
            "export_hidden": self.config.export_hidden,
            "include_cameras": self.config.include_cameras,
            "include_lights": self.config.include_lights,
        }
        (staging / "engine_config_snapshot.json").write_text(
            json.dumps(config_snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        copied.append("engine_config_snapshot.json")

        script_stat = script_path.stat()
        summary = {
            "job_id": job_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error),
            "source_max": str(source_max),
            "output_glb": str(output_glb),
            "work_dir": str(work),
            "max_command": max_cmd or [],
            "run_job_ms": {
                "path": str(script_path),
                "sha256": self._sha256(script_path),
                "size_bytes": script_stat.st_size,
                "modified_utc": datetime.fromtimestamp(script_stat.st_mtime, timezone.utc).isoformat(),
                "line_count": len(script_path.read_text(encoding="utf-8", errors="replace").splitlines()),
            },
            "artifacts_included": copied,
            "send_this_file_for_support": bundle_path.name,
        }
        (staging / "diagnostic_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (staging / "README_SEND_THIS_ZIP.txt").write_text(
            "Send the complete *_diagnostics.zip file. It contains the exact deployed MAXScript, "
            "numbered source, process logs, job payload, configuration snapshot, and any intermediate "
            "files created before the failure.\n",
            encoding="utf-8",
        )

        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(staging.iterdir()):
                if item.is_file():
                    archive.write(item, arcname=item.name)

        latest_zip = diagnostics_root / "Latest_Diagnostics.zip"
        shutil.copy2(bundle_path, latest_zip)
        (diagnostics_root / "Latest_Diagnostics.txt").write_text(
            str(bundle_path), encoding="utf-8"
        )
        return bundle_path

    def _diagnostics_root(self) -> Path:
        root = self.runtime_root / "logs"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _create_emergency_diagnostics(
        self, *, job_id: str, error: BaseException, context: dict | None = None
    ) -> Path:
        """Last-resort bundle that must work even when normal diagnostics fail."""
        diagnostics_root = self._diagnostics_root()
        bundle_path = diagnostics_root / f"{job_id}_diagnostics.zip"
        payload = {
            "job_id": job_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
        }
        emergency_json = diagnostics_root / f"{job_id}_emergency_diagnostic.json"
        emergency_json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(emergency_json, arcname=emergency_json.name)
        latest_zip = diagnostics_root / "Latest_Diagnostics.zip"
        shutil.copy2(bundle_path, latest_zip)
        (diagnostics_root / "Latest_Diagnostics.txt").write_text(
            str(bundle_path), encoding="utf-8"
        )
        return bundle_path

    def convert(self, source_max: Path, output_glb: Path) -> ConversionReport:
        source_max = source_max.resolve()
        output_glb = output_glb.resolve()
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        report = ConversionReport(
            str(source_max), str(output_glb), "", datetime.now(timezone.utc).isoformat()
        )
        work = self.runtime_root / "temp" / job_id
        logs_root = self.runtime_root / "logs"
        final_report_path = logs_root / f"{job_id}.json"
        script_path = self.root / "maxscripts" / "run_job.ms"
        input_json = work / "job.json"
        report_json = work / "max_report.json"
        texture_manifest = work / "texture_manifest.json"
        fbx_path = work / "scene.fbx"
        intermediate_glb = work / "preview.glb"
        max_cmd: list[str] | None = None

        try:
            logs_root.mkdir(parents=True, exist_ok=True)
            work.mkdir(parents=True, exist_ok=False)
            report.work_dir = str(work)

            if source_max.suffix.lower() != ".max" or not source_max.is_file():
                raise FileNotFoundError(f"Valid .max file required: {source_max}")
            if not Path(self.config.max_exe).is_file():
                raise FileNotFoundError(f"3ds Max executable not found: {self.config.max_exe}")
            if not Path(self.config.blender_exe).is_file():
                raise FileNotFoundError(f"Blender executable not found: {self.config.blender_exe}")
            if not script_path.is_file():
                raise FileNotFoundError(f"MAXScript not found: {script_path}")

            output_glb.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source_max": str(source_max),
                "output_fbx": str(fbx_path),
                "report_json": str(report_json),
                "texture_manifest": str(texture_manifest),
                "export_hidden": self.config.export_hidden,
                "include_cameras": self.config.include_cameras,
                "include_lights": self.config.include_lights,
            }
            input_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            max_exe = Path(self.config.max_exe)
            batch_exe = max_exe.with_name("3dsmaxbatch.exe")
            if not batch_exe.is_file():
                raise FileNotFoundError(f"3ds Max Batch executable not found: {batch_exe}")
            batch_log = logs_root / f"{job_id}_max_batch.log"
            listener_log = logs_root / f"{job_id}_max_listener.log"
            system_log = logs_root / f"{job_id}_max_system.log"
            job_arg = "jobPath:" + str(input_json).replace("\\", "/")
            max_cmd = [
                str(batch_exe), str(script_path), "-v", "3", "-dm", "on",
                "-listenerlog", str(listener_log), "-log", str(system_log),
                "-mxsString", job_arg,
            ]
            run_process(
                max_cmd, self.root, self.config.timeout_seconds, batch_log,
                extra_env={
                    "COMPASS_JOB_PATH": str(input_json),
                    "ADSK_APPLICATION_PLUGINS": "",
                },
                allow_failure=True, hidden=True,
            )
            if not fbx_path.is_file():
                raise RuntimeError(
                    "Background 3ds Max conversion failed. "
                    f"See {batch_log}, {system_log}, and {listener_log}"
                )
            if report_json.is_file():
                report.max_report = json.loads(report_json.read_text(encoding="utf-8"))

            blender_cmd = [
                self.config.blender_exe, "--background", "--factory-startup",
                "--python", str(self.root / "blender" / "fbx_to_glb.py"),
                "--", "--input", str(fbx_path), "--output", str(intermediate_glb),
                "--texture-manifest", str(texture_manifest),
            ]
            blender_log = logs_root / f"{job_id}_blender.log"
            run_process(blender_cmd, self.root, self.config.timeout_seconds, blender_log)
            if not intermediate_glb.is_file():
                raise RuntimeError(f"GLB not created: {intermediate_glb}. See {blender_log}")
            report.validation = validate_glb(intermediate_glb)
            shutil.copy2(intermediate_glb, output_glb)

            # A conversion can technically succeed while still producing an unusable
            # preview (for example, materials are present but Blender imported zero
            # images). That is the exact case support diagnostics are needed for, so
            # create the bundle before the successful job's temp folder is cleaned.
            validation = report.validation or {}
            material_count = int(validation.get("materials", 0) or 0)
            image_count = int(validation.get("images", 0) or 0)
            if material_count > 0 and image_count == 0:
                warning = RuntimeError(
                    "GLB validation warning: materials were exported but no texture images "
                    "were embedded or linked."
                )
                try:
                    diagnostics = self._create_diagnostics_bundle(
                        job_id=job_id, logs_root=logs_root, work=work,
                        script_path=script_path, input_json=input_json,
                        report_json=report_json, texture_manifest=texture_manifest,
                        fbx_path=fbx_path, intermediate_glb=intermediate_glb,
                        source_max=source_max, output_glb=output_glb,
                        error=warning, max_cmd=max_cmd,
                    )
                except Exception as diagnostics_error:
                    diagnostics = self._create_emergency_diagnostics(
                        job_id=job_id, error=warning,
                        context={
                            "diagnostics_error": str(diagnostics_error),
                            "validation": validation,
                            "source_max": str(source_max),
                            "output_glb": str(output_glb),
                        },
                    )
                report.diagnostics_zip = str(diagnostics)
                report.error = f"{warning} Diagnostic package: {diagnostics}"

            report.status = "success"
            report.completed_utc = datetime.now(timezone.utc).isoformat()
            return report
        except Exception as exc:
            context = {
                "source_max": str(source_max),
                "output_glb": str(output_glb),
                "runtime_root": str(self.runtime_root),
                "engine_root": str(self.root),
                "work_dir": str(work),
                "max_exe": self.config.max_exe,
                "blender_exe": self.config.blender_exe,
            }
            try:
                diagnostics = self._create_diagnostics_bundle(
                    job_id=job_id, logs_root=logs_root, work=work,
                    script_path=script_path, input_json=input_json,
                    report_json=report_json, texture_manifest=texture_manifest,
                    fbx_path=fbx_path, intermediate_glb=intermediate_glb,
                    source_max=source_max, output_glb=output_glb,
                    error=exc, max_cmd=max_cmd,
                )
            except Exception as diagnostics_error:
                context["diagnostics_error"] = str(diagnostics_error)
                diagnostics = self._create_emergency_diagnostics(
                    job_id=job_id, error=exc, context=context
                )
            report.status = "failed"
            report.diagnostics_zip = str(diagnostics)
            report.error = f"{exc} Diagnostic package: {diagnostics}"
            report.completed_utc = datetime.now(timezone.utc).isoformat()
            raise RuntimeError(report.error) from exc
        finally:
            try:
                logs_root.mkdir(parents=True, exist_ok=True)
                final_report_path.write_text(
                    json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8"
                )
            except Exception:
                pass
            if not self.config.keep_temp and report.status == "success":
                shutil.rmtree(work, ignore_errors=True)
